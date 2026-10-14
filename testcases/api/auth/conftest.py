import pytest
import uuid
from utils.test_data_util import create_test_user, delete_test_user


@pytest.fixture(scope="module", autouse=True)
def auth_base_accounts(prepared_accounts):
    """认证模块基础账号前置，保证普通用户和管理员账号已存在。"""
    return prepared_accounts


class UserCleanup:
    """注册用例临时用户清理器。"""

    def __init__(self, db):
        self.db = db
        self.usernames = []

    def add(self, username):
        """记录临时用户，并先清理历史残留，避免重复执行时账号已存在。"""
        if not username:
            return
        self.db.execute(
            "DELETE FROM users WHERE username = %s",
            (username,),
        )
        if username not in self.usernames:
            self.usernames.append(username)

    append = add

    def cleanup(self):
        for username in self.usernames:
            self.db.execute(
                "DELETE FROM users WHERE username = %s",
                (username,),
            )


@pytest.fixture(scope="function")
def user_cleanup(db):
    """注册后置清理"""
    cleanup = UserCleanup(db)
    yield cleanup
    cleanup.cleanup()


@pytest.fixture(scope="function")
def disabled_user(db):
    """创建禁用用户，用于测试禁用账号登录"""
    username = f"disabled_user_{uuid.uuid4().hex[:8]}"
    password = "123456"

    user = create_test_user(
        db=db,
        username=username,
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
    """创建已存在用户，用于测试注册账号重复"""
    username = f"existing_user_{uuid.uuid4().hex[:8]}"
    password = "123456"
    user = create_test_user(
        db=db,
        username=username,
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
