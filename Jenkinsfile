pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        booleanParam(
            name: 'REBUILD_ENVS',
            defaultValue: false,
            description: '强制重建后端和测试虚拟环境'
        )
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    environment {
        BACKEND_REPO = 'https://github.com/000Revan/lab_agent_backend.git'

        BACKEND_ENV_ID = '8038e576-3bd9-4202-bae7-32ca8233cc33'
        TEST_CONFIG_ID = 'f52feba3-d818-4ce9-bf96-dfa2b17428e9'

        MAIL_TO = '2329087615@qq.com'
        ALLURE_COMMANDLINE = 'allure2'

        PYTHONUTF8 = '1'
        PYTHONUNBUFFERED = '1'
    }

    stages {
        stage('清理旧代码状态') {
            steps {
                script {
                    // 动态标记不要放入environment块。
                    env.REPORTS_CURRENT = 'false'

                    if (isUnix()) {
                        error('此Jenkinsfile需要在Windows节点运行')
                    }

                    // 仅清理代码目录。
                    // 保留.git目录和工作区根目录下的.ci环境缓存。
                    for (repo in ['tests', 'backend']) {
                        if (fileExists("${repo}/.git")) {
                            dir(repo) {
                                bat '''
                                    @echo off
                                    git reset --hard HEAD
                                    if errorlevel 1 exit /b 1

                                    git clean -ffdx
                                    if errorlevel 1 exit /b 1
                                '''
                            }
                        } else if (fileExists(repo)) {
                            dir(repo) {
                                deleteDir()
                            }
                        }
                    }
                }
            }
        }

        stage('检出代码') {
            steps {
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
                                ]],
                                extensions: [
                                    [$class: 'PruneStaleBranch']
                                ]
                            ]
                        )

                        env.BACKEND_COMMIT = info.GIT_COMMIT
                    }
                }
            }
        }

        stage('清理本次运行目录') {
            steps {
                // 防止本次构建使用上一次遗留的测试报告。
                dir('tests/reports') {
                    deleteDir()
                }

                dir('tests/logs') {
                    deleteDir()
                }

                dir('backend/uploads') {
                    deleteDir()
                }

                dir('backend/data/chroma') {
                    deleteDir()
                }
            }
        }

        stage('生成CI脚本') {
            steps {
                writeFile(
                    file: 'ci_runtime.py',
                    encoding: 'UTF-8',
                    text: '''
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
TESTS = ROOT / "tests"
CACHE = ROOT / ".ci"

BACKEND_PYTHON = (
    CACHE / "venv-backend" / "Scripts" / "python.exe"
)
TEST_PYTHON = (
    CACHE / "venv-tests" / "Scripts" / "python.exe"
)

CONFIG_PATH = TESTS / "config" / "config.yaml"
REPORTS = TESTS / "reports"

DATABASE = "lab_agent_test"
HOST = "127.0.0.1"
PORT = 18000
BASE_URL = f"http://{HOST}:{PORT}"

# 修改环境准备策略时递增，使旧缓存失效。
ENV_SCHEMA = "v1"


def requirements_files(project):
    """收集requirements及通过-r/-c引用的本地文件。"""
    discovered = set()

    def visit(path):
        path = path.resolve()

        # 引用文件必须位于当前项目内。
        path.relative_to(project.resolve())

        if path in discovered:
            return

        if not path.is_file():
            raise FileNotFoundError(
                f"依赖文件不存在：{path}"
            )

        discovered.add(path)

        for raw_line in path.read_text(
            encoding="utf-8-sig"
        ).splitlines():
            line = raw_line.strip()

            for prefix in (
                "--requirement=",
                "--requirement ",
                "--constraint=",
                "--constraint ",
                "-r",
                "-c",
            ):
                if line.startswith(prefix):
                    referenced = line[len(prefix):].strip()
                    referenced = referenced.strip(
                        chr(34) + chr(39)
                    )
                    visit(path.parent / referenced)
                    break

    visit(project / "requirements.txt")
    return sorted(discovered)


def environment_fingerprint(project):
    digest = hashlib.sha256()

    identity = {
        "schema": ENV_SCHEMA,
        "workspace": str(ROOT),
        "python": str(Path(sys.executable).resolve()),
        "version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.machine(),
    }

    digest.update(
        json.dumps(
            identity, sort_keys=True
        ).encode("utf-8")
    )

    for path in requirements_files(project):
        relative = path.relative_to(project.resolve())
        digest.update(str(relative).encode("utf-8"))
        digest.update(path.read_bytes())

    return digest.hexdigest()


def prepare_environment(name):
    if name not in ("backend", "tests"):
        raise ValueError("未知环境名称")

    project = ROOT / name
    CACHE.mkdir(parents=True, exist_ok=True)

    environment = CACHE / f"venv-{name}"
    python = environment / "Scripts" / "python.exe"
    marker = CACHE / f"{name}.sha256"

    # 避免环境目录通过链接指向缓存目录之外。
    environment.resolve().relative_to(CACHE.resolve())

    fingerprint = environment_fingerprint(project)

    rebuild = os.getenv(
        "CI_REBUILD_ENVS", "false"
    ).lower() == "true"

    reusable = (
        not rebuild
        and python.is_file()
        and marker.is_file()
        and marker.read_text(
            encoding="utf-8"
        ).strip() == fingerprint
    )

    if reusable:
        print(
            f"[{name}] 检查已有虚拟环境",
            flush=True,
        )

        try:
            subprocess.run(
                [str(python), "-m", "pip", "check"],
                check=True,
                timeout=60,
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ):
            print(
                f"[{name}] 环境检查失败，将重建",
                flush=True,
            )
        else:
            print(
                f"[{name}] 依赖未变化，复用虚拟环境",
                flush=True,
            )
            return

    # 安装成功前不保留有效指纹。
    marker.unlink(missing_ok=True)

    if environment.exists():
        shutil.rmtree(environment)

    print(
        f"[{name}] 创建虚拟环境",
        flush=True,
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "venv",
            str(environment),
        ],
        check=True,
        timeout=120,
    )

    print(
        f"[{name}] 安装项目依赖",
        flush=True,
    )

    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "-r",
            "requirements.txt",
        ],
        cwd=project,
        check=True,
        timeout=40 * 60,
    )

    subprocess.run(
        [str(python), "-m", "pip", "check"],
        check=True,
        timeout=60,
    )

    # 全部成功后再保存指纹。
    temporary = marker.with_suffix(".tmp")
    temporary.write_text(
        fingerprint, encoding="utf-8"
    )
    temporary.replace(marker)

    print(
        f"[{name}] 环境准备完成",
        flush=True,
    )


def prepare_config():
    import yaml

    config = yaml.safe_load(
        CONFIG_PATH.read_text(encoding="utf-8")
    )

    selected_env = config["envs"]
    selected = config[selected_env]
    db = selected["db"]

    if db["database"] != DATABASE:
        raise ValueError(
            "CI只允许操作lab_agent_test数据库"
        )

    if selected["base_url"].rstrip("/") != BASE_URL:
        raise ValueError(
            "测试base_url应为http://127.0.0.1:18000"
        )

    selected["upload_dir"] = str(
        (BACKEND / "uploads").resolve()
    )

    CONFIG_PATH.write_text(
        yaml.safe_dump(
            config, allow_unicode=True
        ),
        encoding="utf-8",
    )

    # 使用后端自身的配置加载逻辑。
    # 只返回非密码字段，不输出完整连接字符串。
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
    import pymysql

    # 不指定database，因为测试数据库可能尚不存在。
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
                "后端提前退出，请查看backend.log"
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

    raise TimeoutError(
        "等待后端就绪超过120秒"
    )


def stop_backend(process):
    if process is None or process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=15)


def run_tests():
    REPORTS.mkdir(parents=True, exist_ok=True)

    # 配置和端口检查通过后，才允许修改数据库。
    selected_env, db = prepare_config()
    check_port()

    process = None
    exit_code = 2

    with (REPORTS / "backend.log").open(
        "w", encoding="utf-8"
    ) as backend_log:
        try:
            print(
                "开始重建测试数据库",
                flush=True,
            )
            reset_database(db)

            print(
                "启动后端服务",
                flush=True,
            )
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

            test_env = os.environ.copy()
            test_env["LAB_TEST_CONFIG"] = str(CONFIG_PATH)
            test_env["LAB_TEST_ENV"] = selected_env

            print(
                "后端已就绪，开始测试",
                flush=True,
            )

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

                print(
                    "删除本次测试数据库",
                    flush=True,
                )
                drop_database(db)

                print(
                    "数据库与进程清理完成",
                    flush=True,
                )

            except Exception:
                traceback.print_exc()
                print(
                    "清理失败，请检查执行节点",
                    file=sys.stderr,
                )
                exit_code = 2

    return exit_code


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "prepare":
        prepare_environment(sys.argv[2])
        return 0

    if sys.argv[1:] == ["test"]:
        return run_tests()

    raise ValueError(
        "用法：prepare backend、prepare tests或test"
    )


if __name__ == "__main__":
    sys.exit(main())
'''
                )
            }
        }

        stage('准备后端环境') {
            steps {
                script {
                    withEnv([
                        "CI_REBUILD_ENVS=${params.REBUILD_ENVS}"
                    ]) {
                        bat '''
                            @echo off
                            py ci_runtime.py prepare backend
                            exit /b %ERRORLEVEL%
                        '''
                    }
                }
            }
        }

        stage('准备测试环境') {
            steps {
                script {
                    withEnv([
                        "CI_REBUILD_ENVS=${params.REBUILD_ENVS}"
                    ]) {
                        bat '''
                            @echo off
                            py ci_runtime.py prepare tests
                            exit /b %ERRORLEVEL%
                        '''
                    }
                }
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
                    script {
                        env.REPORTS_CURRENT = 'true'
                    }

                    bat '''
                        @echo off
                        .ci\\venv-tests\\Scripts\\python.exe ci_runtime.py test
                        exit /b %ERRORLEVEL%
                    '''
                }
            }
        }
    }

    post {
        always {
            script {
                echo "本次报告发布标记：${env.REPORTS_CURRENT}"

                if (env.REPORTS_CURRENT == 'true') {
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
                            error('未生成JUnit报告')
                        } else {
                            echo '本次未生成JUnit报告，请检查失败阶段'
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
                            echo '本次未生成Allure结果，请检查失败阶段'
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
                } else {
                    echo '本次尚未进入测试执行阶段，不发布旧报告'
                }
            }
        }

        cleanup {
            script {
                // 清除注入配置和临时产物。
                // 保留仓库、.git和.ci虚拟环境缓存。
                catchError(
                    buildResult: 'FAILURE',
                    stageResult: 'FAILURE',
                    catchInterruptions: false
                ) {
                    powershell '''
                        $ErrorActionPreference = 'Stop'

                        $temporaryFiles = @(
                            'backend/.env',
                            'tests/config/config.yaml',
                            'ci_runtime.py'
                        )

                        foreach ($item in $temporaryFiles) {
                            if (Test-Path -LiteralPath $item) {
                                Remove-Item -LiteralPath $item -Force
                            }
                        }
                    '''

                    dir('backend/uploads') {
                        deleteDir()
                    }

                    dir('backend/data/chroma') {
                        deleteDir()
                    }

                    dir('tests/logs') {
                        deleteDir()
                    }
                }

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
强制重建环境：${params.REBUILD_ENVS}

构建地址：${env.BUILD_URL}
JUnit报告：${env.BUILD_URL}testReport/
Allure报告：${env.BUILD_URL}allure/

如果构建在测试前失败，或报告发布失败，对应报告可能不可用。
后端日志请在构建页面的Artifacts中查看backend.log。
"""
                )
            }
        }
    }
}