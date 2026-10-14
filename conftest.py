# 全局 fixture

import pytest
from common.context import TestContext
from common.logger import get_logger
from common.request_client import RequestClient
from database.mysql_client import MySQLClient
from utils.yaml_util import load_config_yaml, load_env_config
from utils.account_util import validate_account_config, upsert_test_account
from utils.test_data_util import create_test_user, delete_test_user, unique_name
from api.auth_api import AuthApi
from api.user_api import UserApi
from api.lab_api import LabApi
from api.equipment_api import EquipmentApi
from api.reservation_api import ReservationApi
from api.file_api import FileApi

logger = get_logger("conftest")


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
