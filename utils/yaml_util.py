# 文件读取工具
import yaml
from pydantic import ValidationError

from schemas.test_case import BaseApiCase
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
    """读取并校验测试数据 YAML，返回兼容 pytest 参数化的字典。"""
    file_path = get_data_path(filename)
    raw_data = load_yaml(file_path)

    if not isinstance(raw_data, dict):
        raise ValueError(f"测试数据文件必须是映射结构：{file_path}")

    validated_data = {}
    for section, cases in raw_data.items():
        if not isinstance(section, str) or not section.strip():
            raise ValueError(f"测试数据分组名称不能为空：{file_path}")
        if not isinstance(cases, list):
            raise ValueError(f"测试数据分组必须是列表：{filename} -> {section}")

        validated_cases = []
        for index, case in enumerate(cases, start=1):
            try:
                validated_case = BaseApiCase.model_validate(case)
            except ValidationError as exc:
                raise ValueError(
                    f"测试数据契约校验失败：{filename} -> {section}[{index}]\n{exc}"
                ) from exc

            # 仅输出 YAML 中实际声明的可选字段，兼容现有 dict 读取方式。
            validated_cases.append(
                validated_case.model_dump(mode="python", exclude_unset=True)
            )

        validated_data[section] = validated_cases

    return validated_data


def load_env_config(filename="config.yaml"):
    """读取当前环境配置"""
    all_config = load_config_yaml(filename)
    env = all_config.get("envs")
    if not env:
        raise KeyError("config.yaml 中缺少 envs 配置")
    if env not in all_config:
        raise KeyError(f"config.yaml 中不存在环境配置：{env}")
    return all_config[env]
