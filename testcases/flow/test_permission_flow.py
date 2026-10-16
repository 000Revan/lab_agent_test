import allure
import pytest

from utils.assert_util import assert_common_response


pytestmark = [
    pytest.mark.flow,
    pytest.mark.usefixtures("clean_temp"),
    allure.epic("实验室预约系统"),
    allure.feature("接口联调 Flow"),
]


@allure.story("同一资源的角色权限边界")
@allure.severity(allure.severity_level.CRITICAL)
def test_anonymous_user_admin_permission_flow(api_factory, temp_lab, ctx):
    """围绕同一实验室验证未登录、普通用户和管理员的权限递进。"""
    ctx.set_temp("permission_lab_id", temp_lab["id"])
    anonymous_lab_api = api_factory("lab", role="anonymous")
    user_lab_api = api_factory("lab", role="user")
    admin_lab_api = api_factory("lab", role="admin")

    with allure.step("未登录用户不能查询实验室"):
        assert_common_response(
            anonymous_lab_api.detail(ctx.get_temp("permission_lab_id")),
            {
                "http_status": 401,
                "code": 401,
                "message": "Not authenticated",
                "data": None,
            },
        )

    with allure.step("普通用户可以读取实验室"):
        detail_body = assert_common_response(
            user_lab_api.detail(ctx.get_temp("permission_lab_id")),
            {"http_status": 200, "code": 200, "message": "请求成功"},
        )
        assert detail_body["data"]["id"] == ctx.get_temp("permission_lab_id")

    with allure.step("普通用户不能修改实验室"):
        assert_common_response(
            user_lab_api.update(
                ctx.get_temp("permission_lab_id"), {"location": "无权限修改"}
            ),
            {
                "http_status": 200,
                "code": 403,
                "message": "无权限访问",
                "data": None,
            },
        )

    with allure.step("管理员修改同一实验室"):
        updated_location = "Flow权限验证区"
        update_body = assert_common_response(
            admin_lab_api.update(
                ctx.get_temp("permission_lab_id"),
                {"location": updated_location},
            ),
            {"http_status": 200, "code": 200, "message": "请求成功"},
        )
        assert update_body["data"]["location"] == updated_location

    with allure.step("普通用户可以读取管理员修改后的结果"):
        detail_body = assert_common_response(
            user_lab_api.detail(ctx.get_temp("permission_lab_id")),
            {"http_status": 200, "code": 200, "message": "请求成功"},
        )
        assert detail_body["data"]["location"] == updated_location
