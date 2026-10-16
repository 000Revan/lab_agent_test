import pytest

from utils.test_data_util import create_test_user, delete_test_user, unique_name


@pytest.fixture(scope="function")
def unique_user_username():
    """为管理员创建用户用例生成不会互相冲突的账号。"""
    return unique_name("admin_create_user")


@pytest.fixture(scope="function")
def not_exists_user_id(db):
    """生成当前 users 表中不存在的用户 ID。"""
    result = db.query_one("SELECT COALESCE(MAX(id), 0) + 10000 AS user_id FROM users")
    return result["user_id"]


@pytest.fixture(scope="function")
def query_user(db):
    """根据用户 ID 查询数据库用户信息"""

    def query(*, user_id=None, username=None):
        if (user_id is None) == (username is None):
            raise ValueError("user_id 和 username 必须且只能传入一个")

        if user_id is not None:
            condition = "id"
            value = user_id
        else:
            condition = "username"
            value = username

        return db.query_one(
            f"""
            SELECT *
            FROM users
            WHERE {condition} = %s
            LIMIT 1
            """,
            (value,),
        )

    return query
