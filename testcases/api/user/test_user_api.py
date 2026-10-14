# 用户信息、修改资料、修改密码、用户管理接口测试
import allure
import pytest

from utils.assert_util import (
    assert_common_response,
    assert_database_expectation,
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

    @allure.story("获取用户列表接口")
    def test_admin_list_users(self, api_factory):
        """管理员查询用户列表用例"""
        user_api = api_factory("user", role="admin")
        payload = {"page": 1, "pagesize": 10}
        expect = {
            "http_status": 200,
            "code": 200,
            "message": "请求成功",
            "data_keys": ["list", "total"],
        }
        res = user_api.list(payload)
        assert_common_response(res, expect)

    @allure.story("管理员创建用户接口")
    def test_admin_create_user(self, api_factory, delete_test_user_by_username):
        """管理员创建用户用例"""
        user_api = api_factory("user", role="admin")
        payload = {
            "username": "test_admin_create_user",
            "name": "管理员创建用户",
            "email": "xxx@163.com",
            "phone": "13333333333",
        }
        delete_test_user_by_username(payload["username"])
        expect = {
            "http_status": 200,
            "code": 200,
            "message": "请求成功",
            "data_keys": [
                "id",
                "username",
                "name",
                "role",
                "email",
                "phone",
                "avatar",
                "status",
            ],
        }
        res = user_api.create(payload)
        body = assert_common_response(res, expect)

    @allure.story("管理员修改用户信息接口")
    def test_admin_update_user(self, api_factory, temp_user_account):
        """管理员修改指定用户用例"""
        user_id = temp_user_account.get("id")
        payload = {
            "name": "管理员修改测试",
            "email": "ddd@163.com",
            "status": 1,
            "role": "admin",
        }
        expect = {
            "http_status": 200,
            "code": 200,
            "message": "请求成功",
        }
        user_api = api_factory("user", role="admin")
        res = user_api.update_by_id(user_id, payload)
        body = assert_common_response(res, expect)

    @allure.story("管理员删除用户接口")
    def test_admin_delete_user(self, api_factory, temp_user_account):
        """管理员删除用户用例"""
        expect = {
            "http_status": 200,
            "code": 200,
            "message": "请求成功",
        }
        user_api = api_factory("user", role="temp_admin")
        res = user_api.delete(temp_user_account.get("id"))
        body = assert_common_response(res, expect)
