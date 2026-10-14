# 登录、注册接口测试用例

import pytest
import allure

from utils.assert_util import (
    assert_common_response,
    assert_data_field_type,
    assert_data_keys_exist,
)
from utils.yaml_util import load_data_yaml

auth_data = load_data_yaml("auth_data.yaml")


login_success_list = auth_data["login_success"]
login_fail_list = auth_data["login_fail"]

register_success_list = auth_data["register_success"]
register_fail_list = auth_data["register_fail"]


pytestmark = [
    allure.epic("实验室预约系统"),
    allure.feature("认证模块"),
]


class TestAuthApi:
    @allure.story("登录接口")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize(
        "case",
        login_success_list,
        ids=[case["title"] for case in login_success_list],
    )
    def test_login_success(self, api_factory, case):
        """登录成功用例"""
        allure.dynamic.title(case["title"])

        auth_api = api_factory("auth", role=case.get("role", "anonymous"))

        with allure.step("发送登录请求"):
            res = auth_api.login(case["payload"])
        with allure.step("断言通用响应"):
            body = assert_common_response(res, case["expect"])
        with allure.step("断言登录业务数据"):
            assert_data_field_type(body, "token", str)
            assert_data_field_type(body, "user", dict)

            data = assert_data_keys_exist(body, case["expect"]["data_keys"])
            assert data["token"]
            user = data["user"]
            for key in case["expect"].get("user_keys", []):
                assert key in user, f"user内部错误，缺少{key}字段"
            assert user["username"] == case["payload"]["username"]

    @allure.story("登录接口")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize(
        "case",
        login_fail_list,
        ids=[case["title"] for case in login_fail_list],
    )
    def test_login_fail(self, api_factory, case):
        """登录失败用例"""
        allure.dynamic.title(case["title"])

        auth_api = api_factory("auth", role=case.get("role", "anonymous"))

        with allure.step("发送登录请求"):
            res = auth_api.login(case["payload"])

        with allure.step("断言登录失败响应"):
            assert_common_response(res, case["expect"])

    @allure.story("登录接口")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_disabled_user(self, api_factory, disabled_user):
        """禁用用户登录失败用例"""
        allure.dynamic.title("禁用用户登录失败")

        auth_api = api_factory("auth", role="anonymous")

        payload = {
            "username": disabled_user["username"],
            "password": disabled_user["password"],
        }

        with allure.step("发送禁用用户登录请求"):
            res = auth_api.login(payload)

        with allure.step("断言登录失败响应"):
            assert_common_response(
                res,
                {
                    "http_status": 200,
                    "code": 403,
                    "message": "账号已被禁用",
                },
            )

    @allure.story("注册接口")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize(
        "case",
        register_success_list,
        ids=[case["title"] for case in register_success_list],
    )
    def test_register_success(self, api_factory, case, user_cleanup):
        """注册成功用例"""
        allure.dynamic.title(case["title"])

        auth_api = api_factory("auth", role=case.get("role", "anonymous"))
        username = case["payload"].get("username")

        with allure.step("记录并预清理注册用户"):
            user_cleanup.add(username)

        with allure.step("发送注册请求"):
            res = auth_api.register(case["payload"])

        with allure.step("断言注册成功响应"):
            assert_common_response(res, case["expect"])

    @allure.story("注册接口")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize(
        "case",
        register_fail_list,
        ids=[case["title"] for case in register_fail_list],
    )
    def test_register_fail(self, api_factory, case):
        """注册失败用例"""
        allure.dynamic.title(case["title"])

        auth_api = api_factory("auth", role=case.get("role", "anonymous"))

        with allure.step("发送注册请求"):
            res = auth_api.register(case["payload"])

        with allure.step("断言注册失败响应"):
            assert_common_response(res, case["expect"])

    @allure.story("注册接口")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_duplicate_username(self, api_factory, existing_user):
        """注册账号重复用例"""
        allure.dynamic.title("注册账号重复")

        auth_api = api_factory("auth", role="anonymous")

        payload = {
            "username": existing_user["username"],
            "password": existing_user["password"],
        }

        with allure.step("发送重复账号注册请求"):
            res = auth_api.register(payload)

        with allure.step("断言注册失败响应"):
            assert_common_response(
                res,
                {
                    "http_status": 200,
                    "code": 500,
                    "message": "账号已存在",
                },
            )
