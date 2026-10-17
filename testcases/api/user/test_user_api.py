# 用户信息、修改资料、修改密码、用户管理接口测试
import allure
import pytest

from utils.assert_util import (
    KnownBackendBugAssertionError,
    assert_common_response,
    assert_database_expectation,
    raise_if_known_bug_response,
)
from utils.yaml_util import load_data_yaml

user_data = load_data_yaml("user_data.yaml")

get_user_info_case = user_data["user_info_success"] + user_data["user_info_fail"]
update_user_profile_case = (
    user_data["user_profile_update_success"] + user_data["user_profile_update_fail"]
)
update_user_password_case = (
    user_data["user_password_update_success"] + user_data["user_password_update_fail"]
)
update_user_password_known_bug_case = user_data["user_password_update_known_bug"]
admin_list_users_case = (
    user_data["admin_user_list_success"] + user_data["admin_user_list_fail"]
)
admin_create_user_case = (
    user_data["admin_user_create_success"] + user_data["admin_user_create_fail"]
)
admin_update_user_case = (
    user_data["admin_user_update_success"] + user_data["admin_user_update_fail"]
)
admin_delete_user_case = (
    user_data["admin_user_delete_success"] + user_data["admin_user_delete_fail"]
)

pytestmark = [
    allure.epic("实验室预约系统"),
    allure.feature("用户模块"),
]


class TestUserApi:
    @allure.story("获取用户信息接口")
    @pytest.mark.parametrize(
        "case",
        get_user_info_case,
        ids=[case["title"] for case in get_user_info_case],
    )
    def test_get_user_info(self, api_factory, case):
        """用户获取个人信息"""

        user_api = api_factory("user", role=case["role"])

        with allure.step("发送获取信息请求"):
            res = user_api.info()

        with allure.step("断言基础响应"):
            assert_common_response(res, case["expect"])

    @allure.story("修改用户信息接口")
    @pytest.mark.parametrize(
        "case",
        update_user_profile_case,
        ids=[case["title"] for case in update_user_profile_case],
    )
    def test_update_user_profile(
        self, api_factory, temp_user_account, query_user, case
    ):
        """修改当前用户信息"""
        user_api = api_factory("user", role=case["role"])
        with allure.step("发送修改信息请求"):
            res = user_api.update(case["payload"])
        with allure.step("断言基础响应"):
            assert_common_response(res, case["expect"])
        if "db_verify" in case:
            with allure.step("断言数据库数据一致性"):
                user = query_user(user_id=temp_user_account["id"])
                assert_database_expectation(user, case["db_verify"])

    @allure.story("修改密码接口")
    @pytest.mark.parametrize(
        "case",
        update_user_password_case,
        ids=[case["title"] for case in update_user_password_case],
    )
    def test_update_user_password(
        self, api_factory, temp_user_account, query_user, case
    ):
        """修改密码"""
        user_api = api_factory("user", role=case["role"])
        with allure.step("发送修改信息请求"):
            res = user_api.password(case["payload"])
        with allure.step("断言基础响应"):
            assert_common_response(res, case["expect"])
        if "db_verify" in case:
            with allure.step("断言数据库数据一致性"):
                user = query_user(user_id=temp_user_account["id"])
                assert_database_expectation(user, case["db_verify"])

    @allure.story("修改密码接口")
    @pytest.mark.xfail(
        strict=True,
        raises=KnownBackendBugAssertionError,
        reason="BUG-USER-001：新密码为空仍被加密并保存",
    )
    @pytest.mark.parametrize(
        "case",
        update_user_password_known_bug_case,
        ids=[case["title"] for case in update_user_password_known_bug_case],
    )
    def test_update_user_password_known_bug(
        self,
        api_factory,
        temp_user_account,
        query_user,
        case,
    ):
        """空密码应被拒绝，并保持数据库中的原密码不变。"""
        allure.dynamic.title(case["title"])
        user_api = api_factory("user", role=case["role"])

        with allure.step("发送新密码为空的修改密码请求"):
            res = user_api.password(case["payload"])

        raise_if_known_bug_response(
            res,
            http_status=200,
            code=200,
            message="请求成功",
        )

        with allure.step("断言期望的正确响应"):
            assert_common_response(res, case["expect"])
        with allure.step("断言数据库中的原密码未被修改"):
            user = query_user(user_id=temp_user_account["id"])
            assert_database_expectation(user, case["db_verify"])

    @allure.story("获取用户列表接口")
    @pytest.mark.parametrize(
        "case",
        admin_list_users_case,
        ids=[case["title"] for case in admin_list_users_case],
    )
    def test_admin_list_users(self, api_factory, case):
        """管理员查询用户列表用例"""
        user_api = api_factory("user", role=case["role"])
        with allure.step("发送获取用户列表请求"):
            res = user_api.list(case.get("payload"))
        with allure.step("断言用户列表响应"):
            assert_common_response(res, case["expect"])

    @allure.story("管理员创建用户接口")
    @pytest.mark.parametrize(
        "case",
        admin_create_user_case,
        ids=[case["title"] for case in admin_create_user_case],
    )
    def test_admin_create_user(
        self,
        api_factory,
        resolve_case_references,
        delete_test_user_by_username,
        query_user,
        case,
    ):
        """管理员创建用户用例"""
        resolved_case = resolve_case_references(case)
        payload = resolved_case.get("payload") or {}
        username = payload.get("username")
        if username:
            delete_test_user_by_username(username)

        user_api = api_factory("user", role=resolved_case["role"])
        with allure.step("发送管理员创建用户请求"):
            res = user_api.create(payload)
        with allure.step("断言创建用户响应"):
            assert_common_response(res, resolved_case["expect"])

        if "db_verify" in resolved_case:
            with allure.step("断言创建后的数据库记录"):
                user = query_user(username=username)
                assert_database_expectation(user, resolved_case["db_verify"])

    @allure.story("管理员修改用户信息接口")
    @pytest.mark.parametrize(
        "case",
        admin_update_user_case,
        ids=[case["title"] for case in admin_update_user_case],
    )
    def test_admin_update_user(
        self,
        api_factory,
        resolve_case_references,
        query_user,
        case,
    ):
        """管理员修改指定用户用例"""
        resolved_case = resolve_case_references(case)
        user_id = resolved_case["path_params"]["user_id"]
        user_api = api_factory("user", role=resolved_case["role"])

        with allure.step("发送管理员修改用户请求"):
            res = user_api.update_by_id(user_id, resolved_case.get("payload"))
        with allure.step("断言修改用户响应"):
            assert_common_response(res, resolved_case["expect"])

        if "db_verify" in resolved_case:
            with allure.step("断言修改后的数据库记录"):
                user = query_user(user_id=user_id)
                assert_database_expectation(user, resolved_case["db_verify"])

    @allure.story("管理员删除用户接口")
    @pytest.mark.parametrize(
        "case",
        admin_delete_user_case,
        ids=[case["title"] for case in admin_delete_user_case],
    )
    def test_admin_delete_user(
        self,
        api_factory,
        resolve_case_references,
        query_user,
        case,
    ):
        """管理员删除用户用例"""
        resolved_case = resolve_case_references(case)
        user_id = resolved_case["path_params"]["user_id"]
        user_api = api_factory("user", role=resolved_case["role"])

        with allure.step("发送管理员删除用户请求"):
            res = user_api.delete(user_id)
        with allure.step("断言删除用户响应"):
            assert_common_response(res, resolved_case["expect"])

        if "db_verify" in resolved_case:
            with allure.step("断言删除后的数据库记录"):
                user = query_user(user_id=user_id)
                assert_database_expectation(user, resolved_case["db_verify"])
