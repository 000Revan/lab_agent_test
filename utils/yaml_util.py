# 文件读取工具
import yaml
from utils.path_util import get_config_path, get_data_path


def load_yaml(file_path):
    """读取yaml文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def load_config_yaml(filename="config.yaml"):
    """读取config目录下的YAML文件"""
    file_path = get_config_path(filename)
    return load_yaml(file_path)


def load_data_yaml(filename):
    """读取测试数据YAML文件"""
    file_path = get_data_path(filename)
    return load_yaml(file_path)


def load_env_config(filename="config.yaml"):
    """读取当前环境配置"""
    all_config = load_config_yaml(filename)
    env = all_config.get("envs")
    if not env:
        raise KeyError("config.yaml 中缺少 envs 配置")
    if env not in all_config:
        raise KeyError(f"config.yaml 中不存在环境配置：{env}")
    return all_config[env]
