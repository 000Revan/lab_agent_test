# 日志封装，负责控制台/文件日志、敏感信息脱敏
from copy import deepcopy
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from utils.path_util import LOG_DIR, ensure_dir

SENSITIVE_KEYS = {
    "password",
    "passwd",
    "pwd",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
    "set-cookie",
    "api_key",
    "apikey",
    "secret",
    "client_secret",
    "phone",
    "email",
}

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def mask_sensitive(data: Any) -> Any:
    """递归信息脱敏"""
    # 如果是字典
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # 将key统一转换为小写
            normalized_key = str(key).lower()
            # 将-转换为_
            normalized_key = normalized_key.replace("-", "_")
            # 敏感字段兼容
            sensitive_keys = {item.replace("-", "_") for item in SENSITIVE_KEYS}
            if normalized_key in sensitive_keys:
                result[key] = "***"
            else:
                result[key] = mask_sensitive(value)
        return result

    # 如果是列表
    if isinstance(data, list):
        return [mask_sensitive(item) for item in data]

    # 如果是元组
    if isinstance(data, tuple):
        return tuple(mask_sensitive(item) for item in data)
    return data


def safe_log_data(data: Any) -> Any:
    """
    安全日志数据入口
    通过深拷贝，确保日志脱敏不会影响真实请求数据或响应数据
    """
    try:
        return mask_sensitive(deepcopy(data))
    except Exception:
        return str(data)


def get_log_file():
    """获取当天文件路径 按日期记录日志"""
    log_dir = Path(LOG_DIR)
    # 如果目录不存在则创建
    log_dir.mkdir(parents=True, exist_ok=True)
    data_str = datetime.now().strftime("%Y%m%d")
    return log_dir / f"lab_agent_test_{data_str}.log"


def get_logger(name="api_test", level: int = logging.INFO):
    """获取统一日志"""

    logger = logging.getLogger(name)

    # 设置 logger 的最低日志级别为 INFO
    # 低于 INFO 的 DEBUG 日志默认不会输出
    logger.setLevel(level)

    logger.propagate = False

    # 防止重复添加handler
    if logger.handlers:
        return logger
    # 创建日志格式器
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )

    # 创建控制台 handler
    console_handler = logging.StreamHandler()

    # 设置控制台日志级别
    console_handler.setLevel(level)

    # 设置控制台日志格式
    console_handler.setFormatter(formatter)

    # 创建文件 handler
    file_handler = logging.FileHandler(
        filename=get_log_file(),
        encoding="utf-8",
    )

    # 设置文件日志级别
    file_handler.setLevel(level)

    # 设置文件日志格式
    file_handler.setFormatter(formatter)

    # 把控制台 handler 添加到 logger
    logger.addHandler(console_handler)

    # 把文件 handler 添加到 logger
    logger.addHandler(file_handler)

    return logger
