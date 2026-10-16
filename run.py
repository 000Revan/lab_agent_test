import os
import sys

import pytest

from utils.path_util import BASE_DIR
from utils.yaml_util import load_env_config


def main():
    # 固定工作目录，让 pytest.ini、报告和用例路径保持一致。
    os.chdir(BASE_DIR)

    try:
        load_env_config()
    except (OSError, ValueError, KeyError) as exc:
        print(f"测试配置检查失败：{exc}", file=sys.stderr)
        return 4

    return int(pytest.main(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())
