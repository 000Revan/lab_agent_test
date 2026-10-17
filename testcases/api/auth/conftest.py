import pytest

from utils.test_data_util import create_test_user, delete_test_user, unique_name


@pytest.fixture(scope="function")
def register_candidate():
    """生成尚未入库的动态注册账号，避免固定账号造成重复执行冲突。"""
    return {
        "username": unique_name("register_user"),
        "password": "Register@123456",
        "name": "注册测试用户",
    }


@pytest.fixture(scope="function")
def disabled_user(db):
    """创建禁用用户，用于验证禁用账号不能登录。"""
    password = "Auth@123456"

    user = create_test_user(
        db=db,
        username=unique_name("disabled_user"),
        password=password,
        name="禁用用户",
        role="student",
        status=0,
    )

    yield {
        **user,
        "password": password,
    }

    delete_test_user(db, user_id=user["id"])


@pytest.fixture(scope="function")
def existing_user(db):
    """创建已存在用户，用于验证重复账号注册。"""
    password = "Auth@123456"
    user = create_test_user(
        db=db,
        username=unique_name("existing_user"),
        password=password,
        name="已存在用户",
        role="student",
        status=1,
    )
    yield {
        **user,
        "password": password,
    }
    delete_test_user(db, user_id=user["id"])


@pytest.fixture(scope="function")
def query_user(db):
    """按用户名查询认证模块创建的用户，供数据库契约断言使用。"""

    def query(username):
        return db.query_one(
            """
            SELECT *
            FROM users
            WHERE username = %s
            LIMIT 1
            """,
            (username,),
        )

    return query
