pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    environment {
        BACKEND_REPO = 'https://github.com/000Revan/lab_agent_backend.git'

        BACKEND_ENV_ID = '8038e576-3bd9-4202-bae7-32ca8233cc33'
        TEST_CONFIG_ID = 'f52feba3-d818-4ce9-bf96-dfa2b17428e9'

        MAIL_TO = '2329087615@qq.com'

        // 必须与系统管理 → Tools中的工具名称一致
        ALLURE_COMMANDLINE = 'allure2'

        PYTHONUTF8 = '1'
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('检出代码') {
            steps {
                deleteDir()

                dir('tests') {
                    script {
                        def info = checkout scm
                        env.TEST_COMMIT = info.GIT_COMMIT
                    }
                }

                dir('backend') {
                    script {
                        def info = checkout(
                            poll: true,
                            changelog: true,
                            scm: [
                                $class: 'GitSCM',
                                branches: [[name: '*/master']],
                                userRemoteConfigs: [[
                                    url: env.BACKEND_REPO,
                                    credentialsId: 'Github-token'
                                ]]
                            ]
                        )

                        env.BACKEND_COMMIT = info.GIT_COMMIT
                    }
                }
            }
        }

        stage('准备后端环境') {
            steps {
                dir('backend') {
                    bat '''
                        @echo off
                        py -m venv .venv
                        if errorlevel 1 exit /b 1

                        .venv\\Scripts\\python.exe -m pip install -r requirements.txt
                        if errorlevel 1 exit /b 1

                        .venv\\Scripts\\python.exe -m pip check
                        if errorlevel 1 exit /b 1
                    '''
                }
            }
        }

        stage('准备测试环境') {
            steps {
                dir('tests') {
                    bat '''
                        @echo off
                        py -m venv .venv
                        if errorlevel 1 exit /b 1

                        .venv\\Scripts\\python.exe -m pip install -r requirements.txt
                        if errorlevel 1 exit /b 1

                        .venv\\Scripts\\python.exe -m pip check
                        if errorlevel 1 exit /b 1
                    '''
                }
            }
        }

        stage('生成CI执行脚本') {
            steps {
                writeFile(
                    file: 'ci_runtime.py',
                    encoding: 'UTF-8',
                    text: '''
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen

import pymysql
import yaml


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
TESTS = ROOT / "tests"

BACKEND_PYTHON = BACKEND / ".venv" / "Scripts" / "python.exe"
TEST_PYTHON = TESTS / ".venv" / "Scripts" / "python.exe"

CONFIG_PATH = TESTS / "config" / "config.yaml"
REPORTS = TESTS / "reports"

DATABASE = "lab_agent_test"
HOST = "127.0.0.1"
PORT = 18000
BASE_URL = f"http://{HOST}:{PORT}"


def prepare_config():
    config = yaml.safe_load(
        CONFIG_PATH.read_text(encoding="utf-8")
    )

    selected_env = config["envs"]
    selected = config[selected_env]
    db = selected["db"]

    if db["database"] != DATABASE:
        raise ValueError("CI只允许操作lab_agent_test数据库")

    if selected["base_url"].rstrip("/") != BASE_URL:
        raise ValueError(
            "测试base_url应为http://127.0.0.1:18000"
        )

    selected["upload_dir"] = str(
        (BACKEND / "uploads").resolve()
    )

    CONFIG_PATH.write_text(
        yaml.safe_dump(config, allow_unicode=True),
        encoding="utf-8",
    )

    # 使用后端自己的配置加载逻辑，校验实际数据库目标。
    # 不输出密码或完整连接字符串。
    check_code = """
import json
from app.config import settings
from sqlalchemy.engine import make_url

url = make_url(settings.DATABASE_URL)

print(json.dumps({
    "driver": url.drivername,
    "host": url.host,
    "port": url.port or 3306,
    "database": url.database
}))
"""

    result = subprocess.run(
        [str(BACKEND_PYTHON), "-c", check_code],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )

    actual = json.loads(result.stdout)
    expected = {
        "driver": "mysql+pymysql",
        "host": db["host"],
        "port": int(db.get("port", 3306)),
        "database": DATABASE,
    }

    if actual != expected:
        raise ValueError(
            "后端与测试项目的数据库目标不一致"
        )

    return selected_env, db


def execute_sql(db, sql):
    # 此时测试数据库可能不存在，因此不传database。
    connection = pymysql.connect(
        host=db["host"],
        port=int(db.get("port", 3306)),
        user=db["user"],
        password=db["password"],
        charset=db.get("charset", "utf8mb4"),
        autocommit=True,
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
    finally:
        connection.close()


def drop_database(db):
    # 库名固定，不接受任意库名。
    execute_sql(
        db,
        "DROP DATABASE IF EXISTS `lab_agent_test`",
    )


def reset_database(db):
    drop_database(db)

    execute_sql(
        db,
        "CREATE DATABASE `lab_agent_test` "
        "CHARACTER SET utf8mb4",
    )


def check_port():
    with socket.socket() as listener:
        listener.bind((HOST, PORT))


def wait_backend(process):
    deadline = time.monotonic() + 120

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                "后端启动失败，请查看归档的backend.log"
            )

        try:
            with urlopen(
                BASE_URL + "/", timeout=2
            ) as response:
                if response.status == 200:
                    return
        except OSError:
            pass

        time.sleep(1)

    raise TimeoutError("等待后端就绪超过120秒")


def stop_backend(process):
    if process is None or process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=15)


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)

    # 校验失败时不进行数据库删除操作。
    selected_env, db = prepare_config()
    check_port()

    process = None
    exit_code = 2

    with (REPORTS / "backend.log").open(
        "w", encoding="utf-8"
    ) as backend_log:
        try:
            print("开始重建测试数据库", flush=True)
            reset_database(db)

            print("启动后端服务", flush=True)
            process = subprocess.Popen(
                [
                    str(BACKEND_PYTHON),
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    HOST,
                    "--port",
                    str(PORT),
                ],
                cwd=BACKEND,
                stdout=backend_log,
                stderr=subprocess.STDOUT,
            )

            wait_backend(process)

            print(
                "后端已就绪，开始运行测试",
                flush=True,
            )

            test_env = os.environ.copy()
            test_env["LAB_TEST_CONFIG"] = str(CONFIG_PATH)
            test_env["LAB_TEST_ENV"] = selected_env

            result = subprocess.run(
                [str(TEST_PYTHON), "run.py"],
                cwd=TESTS,
                env=test_env,
                timeout=20 * 60,
            )

            exit_code = result.returncode

            print(
                f"测试进程退出码：{exit_code}",
                flush=True,
            )

        except Exception:
            traceback.print_exc()
            exit_code = 2

        finally:
            try:
                print(
                    "停止本次后端进程",
                    flush=True,
                )
                stop_backend(process)

                # 确认后端停止后再删库。
                print(
                    "删除本次测试数据库",
                    flush=True,
                )
                drop_database(db)

                print("清理完成", flush=True)

            except Exception:
                traceback.print_exc()
                print(
                    "清理失败，请检查执行节点",
                    file=sys.stderr,
                )
                exit_code = 2

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
'''
                )
            }
        }

        stage('注入配置并执行测试') {
            steps {
                configFileProvider([
                    configFile(
                        fileId: env.BACKEND_ENV_ID,
                        targetLocation: 'backend/.env'
                    ),
                    configFile(
                        fileId: env.TEST_CONFIG_ID,
                        targetLocation: 'tests/config/config.yaml'
                    )
                ]) {
                    bat '''
                        @echo off
                        tests\\.venv\\Scripts\\python.exe ci_runtime.py
                        exit /b %ERRORLEVEL%
                    '''
                }
            }
        }
    }

    post {
        always {
            script {
                // 各种报告独立处理：
                // 某一种发布失败，不跳过其余报告和日志归档。

                catchError(
                    buildResult: 'FAILURE',
                    stageResult: 'FAILURE',
                    catchInterruptions: false
                ) {
                    if (fileExists('tests/reports/junit.xml')) {
                        junit(
                            testResults: 'tests/reports/junit.xml',
                            allowEmptyResults: false
                        )
                    } else if (
                        currentBuild.currentResult == 'SUCCESS'
                    ) {
                        error('未生成JUnit报告，不能判定测试成功')
                    } else {
                        echo '未生成JUnit报告，请检查前面失败的阶段'
                    }
                }

                catchError(
                    buildResult: 'FAILURE',
                    stageResult: 'FAILURE',
                    catchInterruptions: false
                ) {
                    if (fileExists('tests/reports/temps')) {
                        allure(
                            commandline: env.ALLURE_COMMANDLINE,
                            results: [[
                                path: 'tests/reports/temps'
                            ]],
                            reportBuildPolicy: 'ALWAYS'
                        )
                    } else if (
                        currentBuild.currentResult == 'SUCCESS'
                    ) {
                        error('未生成Allure原始结果')
                    } else {
                        echo '未生成Allure原始结果，请检查前面失败的阶段'
                    }
                }

                catchError(
                    buildResult: 'FAILURE',
                    stageResult: 'FAILURE',
                    catchInterruptions: false
                ) {
                    archiveArtifacts(
                        artifacts: 'tests/reports/**/*',
                        allowEmptyArchive: true
                    )
                }
            }
        }

        cleanup {
            script {
                try {
                    def result = currentBuild.currentResult

                    def labels = [
                        SUCCESS: '通过',
                        FAILURE: '失败',
                        UNSTABLE: '不稳定',
                        ABORTED: '已中止'
                    ]

                    def label = labels[result] ?: result

                    emailext(
                        to: env.MAIL_TO,
                        subject: "[${label}] ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                        mimeType: 'text/plain',
                        body: """
构建结果：${result}
任务名称：${env.JOB_NAME}
构建编号：${env.BUILD_NUMBER}

后端提交：${env.BACKEND_COMMIT ?: '未完成检出'}
测试提交：${env.TEST_COMMIT ?: '未完成检出'}

构建地址：${env.BUILD_URL}
JUnit报告：${env.BUILD_URL}testReport/
Allure报告：${env.BUILD_URL}allure/

如果构建在测试前失败，或报告发布失败，对应报告可能不可用。
后端运行日志请在构建页面的Artifacts中查看backend.log。
"""
                    )
                } finally {
                    deleteDir()
                }
            }
        }
    }
}