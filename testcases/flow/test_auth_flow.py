import allure
import pytest

from utils.assert_util import assert_common_response
from utils.test_data_util import unique_name


pytestmark = [
    pytest.mark.flow,
    pytest.mark.smoke,
    pytest.mark.usefixtures("clean_temp"),
    allure.epic("实验室预约系统"),
    allure.feature("接口联调 Flow"),
]


@allure.story("注册登录流程")
@allure.severity(allure.severity_level.CRITICAL)
def test_register_login_and_get_user_info_flow(
    api_factory,
    flow_api_factory,
    delete_test_user_by_username,
    ctx,
):
    """注册新用户后登录，并使用登录 token 获取同一用户的信息。"""
    username = unique_name("flow_user")
    password = "Flow@123456"
    name = "Flow联调用户"
    account = {"username": username, "password": password}

    delete_test_user_by_username(username)
    ctx.set_temp("flow_username", username)
    auth_api = api_factory("auth", role="anonymous")

    with allure.step("注册新的普通用户"):
        register_response = auth_api.register({**account, "name": name})
        assert_common_response(
            register_response,
            {
                "http_status": 200,
                "code": 200,
                "message": "注册成功",
                "data": None,
            },
        )

    with allure.step("使用新注册账号登录并保存 token"):
        login_response = auth_api.login(account)
        login_body = assert_common_response(
            login_response,
            {"http_status": 200, "code": 200, "message": "登录成功"},
        )
        login_data = login_body["data"]
        assert login_data["token"], "登录成功后未返回 token"
        assert login_data["user"]["username"] == username
        ctx.set_temp("flow_token", login_data["token"])
        ctx.set_temp("flow_user_id", login_data["user"]["id"])

    with allure.step("携带登录 token 获取当前用户信息"):
        user_api = flow_api_factory("user", ctx.get_temp("flow_token"))
        info_response = user_api.info()
        info_body = assert_common_response(
            info_response,
            {"http_status": 200, "code": 200, "message": "请求成功"},
        )
        assert info_body["data"]["id"] == ctx.get_temp("flow_user_id")
        assert info_body["data"]["username"] == ctx.get_temp("flow_username")
        assert info_body["data"]["name"] == name
