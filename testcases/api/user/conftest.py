import pytest
from utils.test_data_util import create_test_user, delete_test_user


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
