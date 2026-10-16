# 全局 fixture

import re
from collections.abc import Mapping

import pytest
from common.context import TestContext
from common.logger import get_logger
from common.request_client import RequestClient
from database.mysql_client import MySQLClient
from utils.yaml_util import load_config_yaml, load_env_config
from utils.account_util import validate_account_config, upsert_test_account
from utils.test_data_util import (
    create_test_equipment,
    create_test_lab,
    create_test_user,
    delete_test_equipment,
    delete_test_lab,
    delete_test_user,
    unique_name,
)
from api.auth_api import AuthApi
from api.user_api import UserApi
from api.lab_api import LabApi
from api.equipment_api import EquipmentApi
from api.reservation_api import ReservationApi
from api.file_api import FileApi

logger = get_logger("conftest")

FIXTURE_REFERENCE_PATTERN = re.compile(
    r"^\$\{(?P<fixture>[a-zA-Z_][a-zA-Z0-9_]*)"
    r"(?P<path>(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\}$"
)


def pytest_addoption(parser):
    """注册需要显式开启的慢用例选项。"""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="运行包含大文件上传等高开销慢用例",
    )


def pytest_configure(config):
    """登记 slow 标记，避免 pytest 输出未知标记警告。"""
    config.addinivalue_line("markers", "slow: 高耗时或高资源占用测试")


def pytest_collection_modifyitems(config, items):
    """普通回归默认跳过 slow 用例，使用 --run-slow 显式开启。"""
    if config.getoption("--run-slow"):
        return

    skip_slow = pytest.mark.skip(reason="慢用例需使用 --run-slow 显式执行")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


def _resolve_fixture_reference(value, request):
    """递归解析 YAML 中的 ${fixture.field} 引用，不执行任意表达式。"""
    if isinstance(value, dict):
        return {
            key: _resolve_fixture_reference(item, request)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_resolve_fixture_reference(item, request) for item in value]
    if not isinstance(value, str):
        return value

    matched = FIXTURE_REFERENCE_PATTERN.fullmatch(value)
    if not matched:
        return value

    resolved = request.getfixturevalue(matched.group("fixture"))
    path = matched.group("path").lstrip(".")
    if not path:
        return resolved

    for field_name in path.split("."):
        if isinstance(resolved, Mapping):
            if field_name not in resolved:
                raise KeyError(f"fixture 引用字段不存在：{value}")
            resolved = resolved[field_name]
        else:
            if not hasattr(resolved, field_name):
                raise AttributeError(f"fixture 引用属性不存在：{value}")
            resolved = getattr(resolved, field_name)
    return resolved


@pytest.fixture(scope="function")
def resolve_case_references(request):
    """把参数化用例中的 fixture 引用转换为本次测试的真实值。"""

    def resolve(case):
        return _resolve_fixture_reference(case, request)

    return resolve


@pytest.fixture(scope="session")
def env_config():
    """当前环境配置"""
    return load_env_config()


@pytest.fixture(scope="session")
def api_path():
    """接口路径配置"""
    return load_config_yaml("api_paths.yaml")


@pytest.fixture(scope="session")
def account_config(env_config):
    """账号配置。"""
    return env_config["account"]


@pytest.fixture(scope="session")
def db(env_config):
    """数据库"""
    mysql_client = MySQLClient(env_config["db"]).connect()
    yield mysql_client
    mysql_client.close()


@pytest.fixture(scope="session")
def prepared_accounts(db, account_config):
    """测试账号前置：确保普通用户和管理员账号存在且可登录。"""
    user_account = account_config["user"]
    admin_account = account_config["admin"]
    # 校验配置
    validate_account_config(user_account, "普通用户账号")
    validate_account_config(admin_account, "管理员账号")

    user_id = upsert_test_account(
        db=db,
        username=user_account["username"],
        password=user_account["password"],
        name=user_account.get("name", "测试用户"),
        role=user_account.get("role", "student"),
    )

    admin_id = upsert_test_account(
        db=db,
        username=admin_account["username"],
        password=admin_account["password"],
        name=admin_account.get("name", "测试管理员"),
        role=admin_account.get("role", "admin"),
    )

    return {
        "user": {
            **user_account,
            "id": user_id,
        },
        "admin": {
            **admin_account,
            "id": admin_id,
        },
    }


def create_client(env_config):
    """创建请求客户端。"""
    return RequestClient(
        base_url=env_config["base_url"],
        timeout=env_config.get("timeout", 10),
    )


def login_and_get_token(env_config, api_path, account):
    """登录并获取 token。"""
    login_client = create_client(env_config)
    auth_api = AuthApi(login_client, api_path)
    try:
        res = auth_api.login(account)

        if res.status_code != 200:
            logger.error(f"登录失败，状态码={res.status_code}, 响应={res.text}")
            pytest.fail("登录接口异常，无法获取 token")

        try:
            body = res.json()
        except ValueError:
            logger.error(f"登录接口响应不是 JSON，响应={res.text}")
            pytest.fail("登录接口响应不是 JSON，无法获取 token")

        if body.get("code") != 200:
            logger.error(f"登录业务失败，响应={res.text}")
            pytest.fail("登录业务失败，无法获取 token")

        token = body.get("data", {}).get("token")

        if not token:
            logger.error(f"登录成功但响应中未返回 token，响应={res.text}")
            pytest.fail("登录成功但响应中未返回 token")

        return token

    finally:
        login_client.close()


@pytest.fixture(scope="session")
def client(env_config):
    """基础客户端：不带 token，用于登录、注册、未登录接口。"""
    request_client = create_client(env_config)
    yield request_client
    request_client.close()


@pytest.fixture(scope="session")
def user_client(env_config, api_path, prepared_accounts):
    """普通用户客户端：带普通用户 token。"""
    token = login_and_get_token(
        env_config=env_config,
        api_path=api_path,
        account={
            "username": prepared_accounts["user"]["username"],
            "password": prepared_accounts["user"]["password"],
        },
    )

    request_client = create_client(env_config)
    request_client.set_token(token)

    yield request_client

    request_client.close()


@pytest.fixture(scope="session")
def admin_client(env_config, api_path, prepared_accounts):
    """管理员客户端：带管理员 token。"""
    token = login_and_get_token(
        env_config=env_config,
        api_path=api_path,
        account={
            "username": prepared_accounts["admin"]["username"],
            "password": prepared_accounts["admin"]["password"],
        },
    )

    request_client = create_client(env_config)
    request_client.set_token(token)

    yield request_client

    request_client.close()


@pytest.fixture(scope="function")
def temp_user_account(db):
    """临时普通用户账号：每条用例独立创建，适合会修改用户自身状态的测试。"""
    user = create_test_user(
        db=db,
        username=unique_name("temp_user"),
        password="123456",
        name="临时普通用户",
        role="student",
        status=1,
    )

    yield user

    delete_test_user(db, user_id=user["id"])


@pytest.fixture(scope="function")
def temp_admin_account(db):
    """临时管理员账号：每条用例独立创建，适合管理员身份的破坏性测试。"""
    admin = create_test_user(
        db=db,
        username=unique_name("temp_admin"),
        password="123456",
        name="临时管理员",
        role="admin",
        status=1,
    )

    yield admin

    delete_test_user(db, user_id=admin["id"])


@pytest.fixture(scope="function")
def temp_lab(db):
    """创建用例级临时实验室，供实验室、设备和预约模块复用。"""
    lab = create_test_lab(
        db=db,
        name=unique_name("temp_lab"),
        location="自动化测试楼 A101",
        capacity=30,
        open_time="08:00",
        close_time="18:00",
        description="自动化测试临时实验室",
        status=1,
    )

    yield lab

    delete_test_lab(db, lab_id=lab["id"])


@pytest.fixture(scope="function")
def temp_equipment(db, temp_lab):
    """创建用例级临时设备，供设备和预约模块复用。"""
    equipment = create_test_equipment(
        db=db,
        lab_id=temp_lab["id"],
        name=unique_name("temp_equipment"),
        description="自动化测试临时设备",
        spec="AUTO-SPEC",
        quantity=5,
        status=1,
    )

    yield equipment

    delete_test_equipment(db, equipment_id=equipment["id"])


@pytest.fixture(scope="function")
def delete_test_user_by_username(db):
    usernames = []

    def register(username):
        usernames.append(username)

    yield register
    for username in reversed(usernames):
        delete_test_user(db, username=username)


@pytest.fixture(scope="function")
def temp_user_client(env_config, api_path, temp_user_account):
    """临时普通用户客户端：带随机普通用户 token，用例结束后自动清理账号。"""
    token = login_and_get_token(
        env_config=env_config,
        api_path=api_path,
        account={
            "username": temp_user_account["username"],
            "password": temp_user_account["password"],
        },
    )

    request_client = create_client(env_config)
    request_client.set_token(token)

    yield request_client

    request_client.close()


@pytest.fixture(scope="function")
def temp_admin_client(env_config, api_path, temp_admin_account):
    """临时管理员客户端：带随机管理员 token，用例结束后自动清理账号。"""
    token = login_and_get_token(
        env_config=env_config,
        api_path=api_path,
        account={
            "username": temp_admin_account["username"],
            "password": temp_admin_account["password"],
        },
    )

    request_client = create_client(env_config)
    request_client.set_token(token)

    yield request_client

    request_client.close()


@pytest.fixture(scope="session")
def api_classes():
    """API类映射。"""
    return {
        "auth": AuthApi,
        "user": UserApi,
        "lab": LabApi,
        "equipment": EquipmentApi,
        "reservation": ReservationApi,
        "files": FileApi,
    }


@pytest.fixture(scope="function")
def api_factory(request, api_path, api_classes):
    """API对象工厂，根据模块名和角色创建绑定不同客户端的API对象"""
    client_fixture_map = {
        "anonymous": "client",
        "user": "user_client",
        "admin": "admin_client",
        "temp_user": "temp_user_client",
        "temp_admin": "temp_admin_client",
    }

    def create(module, role="anonymous"):
        if role not in client_fixture_map:
            raise ValueError(f"不支持的客户端角色: {role}")

        if module not in api_classes:
            raise ValueError(f"不支持的API模块: {module}")

        request_client = request.getfixturevalue(client_fixture_map[role])
        api_cls = api_classes[module]
        return api_cls(request_client, api_path)

    return create


@pytest.fixture(scope="session")
def ctx():
    """全局变量fixture"""
    context = TestContext()
    yield context
    context.clear_global()


@pytest.fixture(scope="module")
def module_ctx(ctx):
    """模块变量fixture"""
    yield ctx
    ctx.clear_module()


@pytest.fixture(scope="function")
def clean_temp(ctx):
    """临时变量fixture"""
    ctx.clear_temp()
    yield
    ctx.clear_temp()
