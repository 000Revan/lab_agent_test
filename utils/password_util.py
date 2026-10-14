# 数据库创建账号加密
import bcrypt


# 密码加密
def hash_password(password: str) -> str:
    """对密码进行加密"""
    return bcrypt.hashpw(
        # 进行utf-8标准编码，适用于特殊字符
        password.encode("utf-8"),
        # 加盐
        bcrypt.gensalt(),
    ).decode("utf-8")


# 密码解密,返回bool类型
def verify_password(password: str, hashed_password: str) -> bool:
    """验证密码是否有效"""
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
