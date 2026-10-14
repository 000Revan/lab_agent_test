# 账号准备
from utils.password_util import hash_password


def validate_account_config(account, account_name):
    """校验测试账号配置。"""
    required_keys = ["username", "password"]

    for key in required_keys:
        if not account.get(key):
            raise KeyError(f"{account_name}配置缺少必要字段: {key}")


def upsert_test_account(db, username, password, name, role, status=1):
    """创建或重置测试账号，保证每次测试启动时账号可登录"""
    if not username:
        raise ValueError("测试账号 username 不能为空")
    if not password:
        raise ValueError(f"测试账号 {username} 的 password 不能为空")
    if not role:
        raise ValueError(f"测试账号 {username} 的 role 不能为空")

    password_hash = hash_password(str(password))

    exists = db.query_one(
        "SELECT id FROM users WHERE username = %s LIMIT 1", (username,)
    )
    if exists:
        db.execute(
            """
            UPDATE users
            SET password = %s,
                name = %s,
                role = %s,
                status = %s,
                update_time = NOW()
            WHERE username = %s
            """,
            (password_hash, name, role, status, username),
        )
        return exists["id"]

    db.execute(
        """
        INSERT INTO users (
            username,
            password,
            name,
            role,
            status,
            create_time,
            update_time
        )
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (username, password_hash, name, role, status),
    )
    created = db.query_one(
        "SELECT id FROM users WHERE username = %s LIMIT 1",
        (username,),
    )
    return created["id"]
