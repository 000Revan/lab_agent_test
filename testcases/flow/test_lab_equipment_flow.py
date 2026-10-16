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


@allure.story("实验室设备管理流程")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_lab_equipment_query_and_delete_flow(
    api_factory,
    flow_resource_registry,
    ctx,
):
    """管理员创建实验室和设备，普通用户查询后再由管理员逆序删除。"""
    lab_name = unique_name("flow_lab")
    equipment_name = unique_name("flow_equipment")
    admin_lab_api = api_factory("lab", role="admin")
    admin_equipment_api = api_factory("equipment", role="admin")
    user_lab_api = api_factory("lab", role="user")
    user_equipment_api = api_factory("equipment", role="user")

    with allure.step("管理员创建实验室"):
        lab_response = admin_lab_api.create(
            {
                "name": lab_name,
                "location": "Flow-A101",
                "capacity": 20,
                "open_time": "08:00",
                "close_time": "18:00",
                "description": "接口联调实验室",
                "status": 1,
            }
        )
        lab_body = assert_common_response(
            lab_response,
            {"http_status": 200, "code": 200, "message": "请求成功"},
        )
        lab_id = lab_body["data"]["id"]
        flow_resource_registry["lab_ids"].append(lab_id)
        ctx.set_temp("flow_lab_id", lab_id)

    with allure.step("管理员在刚创建的实验室中创建设备"):
        equipment_response = admin_equipment_api.create(
            {
                "lab_id": ctx.get_temp("flow_lab_id"),
                "name": equipment_name,
                "description": "接口联调设备",
                "spec": "FLOW-SPEC",
                "quantity": 3,
                "status": 1,
            }
        )
        equipment_body = assert_common_response(
            equipment_response,
            {"http_status": 200, "code": 200, "message": "请求成功"},
        )
        equipment_id = equipment_body["data"]["id"]
        flow_resource_registry["equipment_ids"].append(equipment_id)
        ctx.set_temp("flow_equipment_id", equipment_id)

    with allure.step("普通用户按名称查询实验室并查看详情"):
        lab_list_body = assert_common_response(
            user_lab_api.list_lab(
                {"page": 1, "page_size": 20, "keywords": lab_name}
            ),
            {"http_status": 200, "code": 200, "message": "请求成功"},
        )
        assert any(
            item["id"] == ctx.get_temp("flow_lab_id")
            for item in lab_list_body["data"]["list"]
        ), "实验室列表中未找到刚创建的实验室"

        detail_body = assert_common_response(
            user_lab_api.detail(ctx.get_temp("flow_lab_id")),
            {"http_status": 200, "code": 200, "message": "请求成功"},
        )
        assert detail_body["data"]["name"] == lab_name

    with allure.step("普通用户按实验室查询设备"):
        equipment_list_body = assert_common_response(
            user_equipment_api.list(
                {
                    "page": 1,
                    "page_size": 20,
                    "lab_id": ctx.get_temp("flow_lab_id"),
                    "keywords": equipment_name,
                }
            ),
            {"http_status": 200, "code": 200, "message": "请求成功"},
        )
        matched = [
            item
            for item in equipment_list_body["data"]["list"]
            if item["id"] == ctx.get_temp("flow_equipment_id")
        ]
        assert matched, "设备列表中未找到刚创建的设备"
        assert matched[0]["lab_id"] == ctx.get_temp("flow_lab_id")

    with allure.step("管理员按依赖逆序删除设备和实验室"):
        assert_common_response(
            admin_equipment_api.delete(ctx.get_temp("flow_equipment_id")),
            {
                "http_status": 200,
                "code": 200,
                "message": "请求成功",
                "data": None,
            },
        )
        assert_common_response(
            admin_lab_api.delete(ctx.get_temp("flow_lab_id")),
            {
                "http_status": 200,
                "code": 200,
                "message": "删除成功",
                "data": None,
            },
        )
