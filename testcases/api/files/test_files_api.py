# 文件上传接口测试

from pathlib import Path

import allure
import pytest

from utils.assert_util import assert_common_response
from utils.yaml_util import load_data_yaml


file_data = load_data_yaml("file_data.yaml")

file_upload_cases = (
    file_data["file_upload_success"]
    + file_data["file_upload_fail"]
)
file_access_cases = file_data["file_access_success"]


def build_upload_params(cases):
    """把 YAML 中声明的慢用例转换为 pytest 参数标记。"""
    params = []
    for case in cases:
        payload = case.get("payload") or {}
        marks = [pytest.mark.slow] if payload.get("slow") else []
        params.append(pytest.param(case, id=case["title"], marks=marks))
    return params


def register_uploaded_file(response, cleanup):
    """响应成功后立即登记服务端文件，保证后续断言失败时仍能清理。"""
    try:
        body = response.json()
    except ValueError:
        return

    data = body.get("data")
    if isinstance(data, dict) and data.get("disk_name"):
        cleanup(data["disk_name"])


pytestmark = [
    allure.epic("实验室预约系统"),
    allure.feature("文件模块"),
]


class TestFilesApi:
    @allure.story("文件上传接口")
    @pytest.mark.parametrize("case", build_upload_params(file_upload_cases))
    def test_upload_file(
        self,
        api_factory,
        upload_file_factory,
        uploaded_file_cleanup,
        case,
    ):
        """上传文件并校验公共响应和服务端文件元数据。"""
        payload = case.get("payload")
        upload_file = upload_file_factory(payload)
        file_api = api_factory("files", role=case["role"])

        request_options = {}
        if payload and payload.get("slow"):
            request_options["timeout"] = 120

        with allure.step("发送文件上传请求"):
            response = file_api.upload(
                files=upload_file["files"],
                **request_options,
            )
        register_uploaded_file(response, uploaded_file_cleanup)

        with allure.step("断言文件上传响应"):
            body = assert_common_response(response, case["expect"])

        if case["expect"]["code"] != 200:
            return

        data = body["data"]
        expected_suffix = Path(upload_file["filename"]).suffix.lower()

        with allure.step("断言上传文件元数据"):
            assert data["original_name"] == upload_file["filename"], (
                "响应 original_name 与上传文件名不一致"
            )
            assert data["size"] == upload_file["size"], (
                "响应 size 与上传文件大小不一致"
            )
            assert data["disk_name"].endswith(expected_suffix), (
                "服务端文件后缀与上传文件不一致"
            )
            assert data["url"] == f"/uploads/{data['disk_name']}", (
                "响应 url 与 disk_name 不匹配"
            )

    @allure.story("访问上传文件接口")
    @pytest.mark.parametrize(
        "case",
        file_access_cases,
        ids=[case["title"] for case in file_access_cases],
    )
    def test_access_uploaded_file(
        self,
        api_factory,
        upload_file_factory,
        uploaded_file_cleanup,
        case,
    ):
        """上传文件后通过静态 URL 访问，并比对原始二进制内容。"""
        upload_file = upload_file_factory(case["payload"])
        file_api = api_factory("files", role=case["role"])

        with allure.step("准备并上传待访问文件"):
            upload_response = file_api.upload(files=upload_file["files"])
        register_uploaded_file(upload_response, uploaded_file_cleanup)
        upload_body = assert_common_response(
            upload_response,
            file_data["file_upload_success"][0]["expect"],
        )

        disk_name = upload_body["data"]["disk_name"]
        with allure.step("访问已上传文件"):
            access_response = file_api.access(disk_name)

        with allure.step("断言静态文件响应和文件内容"):
            actual_content = assert_common_response(
                access_response,
                case["expect"],
            )
            assert actual_content == upload_file["content"], (
                "访问到的文件内容与上传内容不一致"
            )
            assert access_response.headers["content-type"].startswith(
                case["payload"]["content_type"]
            ), "静态文件响应 Content-Type 不正确"
