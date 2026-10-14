import time
import os
import platform
import pytest
from pathlib import Path
from utils.yaml_util import load_config_yaml, load_env_config
from utils.path_util import (
    ALLURE_REPORT_DIR,
    ALLURE_RESULTS_DIR,
)

ALLURE_RESULT_DIR = Path("./reports/temps")
ALLURE_REPORT_DIR = Path("./reports/allure")


def write_allure_environment():
    """写入 Allure 环境信息。"""

    ALLURE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    all_config = load_config_yaml("config.yaml")
    env = all_config["envs"]
    env_config = load_env_config()

    env_file = ALLURE_RESULTS_DIR / "environment.properties"

    content = [
        f"Project=lab_agent",
        f"Environment={env}",
        f"Base_URL={env_config.get('base_url')}",
        f"Python={platform.python_version()}",
        f"OS={platform.platform()}",
        f"Tester=FUBUKI",
    ]

    env_file.write_text("\n".join(content), encoding="utf-8")


if __name__ == "__main__":
    pytest.main()
    write_allure_environment()
    time.sleep(3)

    os.system("allure generate ./reports/temps -o ./reports/allure --clean")
    os.system("allure open ./reports/allure")
    # subprocess.run(
    #     ["allure", "generate", "./temps", "-o", "./reports/allure", "--clean"],
    #     check=True,
    # )
