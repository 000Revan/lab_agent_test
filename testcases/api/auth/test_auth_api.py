# 登录、注册接口测试用例

import pytest
import allure

from utils.assert_util import (
    KnownBackendBugAssertionError,
    assert_common_response,
    assert_database_expectation,
    raise_if_known_bug_response,
)
from utils.yaml_util import load_data_yaml

auth_data = load_data_yaml("auth_data.yaml")


login_success_list = auth_data["login_success"]
login_fail_list = auth_data["login_fail"]
login_known_bug_list = auth_data["login_known_bug"]

register_success_list = auth_data["register_success"]
register_fail_list = auth_data["register_fail"]
register_duplicate_known_bug_list = auth_data["register_duplicate_known_bug"]
register_validation_known_bug_list = auth_data["register_validation_known_bug"]


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
    def test_login_success(self, api_factory, resolve_case_references, case):
        """登录成功用例"""
        allure.dynamic.title(case["title"])
        resolved_case = resolve_case_references(case)

        auth_api = api_factory("auth", role=resolved_case["role"])

        with allure.step("发送登录请求"):
            res = auth_api.login(resolved_case["payload"])
        with allure.step("断言通用响应"):
            body = assert_common_response(res, resolved_case["expect"])
        with allure.step("断言登录业务数据"):
            data = body["data"]
            assert data["token"].strip(), "登录成功后 token 不应为空"
            user = data["user"]
            assert user["username"] == resolved_case["payload"]["username"]
            assert user["role"] in ("student", "admin")
            assert user["status"] == 1

    @allure.story("登录接口")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize(
        "case",
        login_fail_list,
        ids=[case["title"] for case in login_fail_list],
    )
    def test_login_fail(self, api_factory, resolve_case_references, case):
        """登录失败用例"""
        allure.dynamic.title(case["title"])
        resolved_case = resolve_case_references(case)

        auth_api = api_factory("auth", role=resolved_case["role"])

        with allure.step("发送登录请求"):
            res = auth_api.login(resolved_case.get("payload"))

        with allure.step("断言登录失败响应"):
            assert_common_response(res, resolved_case["expect"])

    @allure.story("登录接口")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.xfail(
        strict=True,
        raises=KnownBackendBugAssertionError,
        reason="BUG-AUTH-002：超长密码未在参数层拦截，bcrypt异常导致500",
    )
    @pytest.mark.parametrize(
        "case",
        login_known_bug_list,
        ids=[case["title"] for case in login_known_bug_list],
    )
    def test_login_known_bug(self, api_factory, resolve_case_references, case):
        """登录参数校验的已知后端缺陷。"""
        allure.dynamic.title(case["title"])
        resolved_case = resolve_case_references(case)
        auth_api = api_factory("auth", role=resolved_case["role"])

        with allure.step("发送登录边界请求"):
            res = auth_api.login(resolved_case["payload"])
        raise_if_known_bug_response(
            res,
            http_status=500,
            code=500,
            message="服务器内部错误",
        )
        with allure.step("断言期望的正确响应"):
            assert_common_response(res, resolved_case["expect"])

    @allure.story("注册接口")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize(
        "case",
        register_success_list,
        ids=[case["title"] for case in register_success_list],
    )
    def test_register_success(
        self,
        api_factory,
        resolve_case_references,
        delete_test_user_by_username,
        query_user,
        case,
    ):
        """注册成功用例"""
        allure.dynamic.title(case["title"])
        resolved_case = resolve_case_references(case)
        payload = resolved_case["payload"]
        username = payload["username"]
        delete_test_user_by_username(username)

        auth_api = api_factory("auth", role=resolved_case["role"])

        with allure.step("发送注册请求"):
            res = auth_api.register(payload)

        with allure.step("断言注册成功响应"):
            assert_common_response(res, resolved_case["expect"])

        with allure.step("断言注册后的数据库记录和密码哈希"):
            user = query_user(username)
            assert_database_expectation(user, resolved_case["db_verify"])

    @allure.story("注册接口")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize(
        "case",
        register_fail_list,
        ids=[case["title"] for case in register_fail_list],
    )
    def test_register_fail(
        self,
        api_factory,
        resolve_case_references,
        delete_test_user_by_username,
        query_user,
        case,
    ):
        """注册失败用例"""
        allure.dynamic.title(case["title"])
        resolved_case = resolve_case_references(case)
        payload = resolved_case.get("payload") or {}
        username = payload.get("username")
        if isinstance(username, str) and username:
            delete_test_user_by_username(username)

        auth_api = api_factory("auth", role=resolved_case["role"])

        with allure.step("发送注册请求"):
            res = auth_api.register(payload)

        with allure.step("断言注册失败响应"):
            assert_common_response(res, resolved_case["expect"])

        if "db_verify" in resolved_case:
            with allure.step("断言注册失败后数据库未产生脏数据"):
                user = query_user(username)
                assert_database_expectation(user, resolved_case["db_verify"])

    @allure.story("注册接口")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.xfail(
        strict=True,
        raises=KnownBackendBugAssertionError,
        reason="BUG-AUTH-001：重复注册错误返回code=500，预期code=400",
    )
    @pytest.mark.parametrize(
        "case",
        register_duplicate_known_bug_list,
        ids=[case["title"] for case in register_duplicate_known_bug_list],
    )
    def test_register_duplicate_username(
        self,
        api_factory,
        resolve_case_references,
        query_user,
        case,
    ):
        """重复账号注册应返回可预期的业务错误。"""
        allure.dynamic.title(case["title"])
        resolved_case = resolve_case_references(case)
        payload = resolved_case["payload"]
        auth_api = api_factory("auth", role=resolved_case["role"])

        with allure.step("发送重复账号注册请求"):
            res = auth_api.register(payload)

        raise_if_known_bug_response(
            res,
            http_status=200,
            code=500,
            message="账号已存在",
        )

        with allure.step("断言期望的正确响应"):
            assert_common_response(res, resolved_case["expect"])

        with allure.step("断言原账号数据未被覆盖"):
            user = query_user(payload["username"])
            assert_database_expectation(user, resolved_case["db_verify"])

    @allure.story("注册接口")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.xfail(
        strict=True,
        raises=KnownBackendBugAssertionError,
        reason="BUG-AUTH-003：超长密码未在参数层拦截，bcrypt异常导致500",
    )
    @pytest.mark.parametrize(
        "case",
        register_validation_known_bug_list,
        ids=[case["title"] for case in register_validation_known_bug_list],
    )
    def test_register_validation_known_bug(
        self,
        api_factory,
        resolve_case_references,
        delete_test_user_by_username,
        query_user,
        case,
    ):
        """注册参数校验的已知后端缺陷。"""
        allure.dynamic.title(case["title"])
        resolved_case = resolve_case_references(case)
        payload = resolved_case["payload"]
        username = payload["username"]
        delete_test_user_by_username(username)
        auth_api = api_factory("auth", role=resolved_case["role"])

        with allure.step("发送注册边界请求"):
            res = auth_api.register(payload)
        raise_if_known_bug_response(
            res,
            http_status=500,
            code=500,
            message="服务器内部错误",
        )
        with allure.step("断言期望的正确响应"):
            assert_common_response(res, resolved_case["expect"])

        with allure.step("断言参数校验失败后未创建用户"):
            user = query_user(username)
            assert_database_expectation(user, resolved_case["db_verify"])
