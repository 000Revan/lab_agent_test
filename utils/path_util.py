# 项目根目录、配置文件路径、报告路径等路径工具
from pathlib import Path

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 配置文件目录
CONFIG_DIR = BASE_DIR / "config"

# 测试数据文件目录
DATA_DIR = BASE_DIR / "data"

# 测试上传文件目录
FILES_DIR = BASE_DIR / "files/upload"

# 日志目录
LOG_DIR = BASE_DIR / "logs"


# Allure 原始结果目录
REPORTS_DIR = BASE_DIR / "reports"
ALLURE_RESULTS_DIR = REPORTS_DIR / "temps"
ALLURE_REPORT_DIR = REPORTS_DIR / "allure"


def get_base_path():
    """获取项目根目录"""
    return BASE_DIR


def get_config_path(filename):
    """获取config配置文件路径"""
    return CONFIG_DIR / filename


def get_data_path(filename):
    """获取测试数据文件路径"""
    return DATA_DIR / filename


def ensure_dir(path):  # 定义函数：确保目录存在
    """确保目录存在，不存在则自动创建。"""  # 函数说明
    path = Path(path)  # 把传入参数转换成 Path 对象
    path.mkdir(
        parents=True, exist_ok=True
    )  # 创建目录，父目录不存在也创建，已存在不报错
    return path  # 返回目录 Path 对象


if __name__ == "__main__":
    print(BASE_DIR)
