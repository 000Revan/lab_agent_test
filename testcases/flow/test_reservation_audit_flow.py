import allure
import pytest

from utils.assert_util import assert_common_response


pytestmark = [
    pytest.mark.flow,
    pytest.mark.smoke,
    pytest.mark.usefixtures("clean_temp"),
    allure.epic("实验室预约系统"),
    allure.feature("接口联调 Flow"),
]


def _find_reservation(items, reservation_id):
    """从预约列表中定位指定预约。"""
    return next((item for item in items if item["id"] == reservation_id), None)


@allure.story("预约审核流程")
@allure.severity(allure.severity_level.BLOCKER)
def test_create_audit_and_query_reservation_flow(
    api_factory,
    temp_user_account,
    temp_equipment,
    flow_reservation_date,
    flow_reservation_registry,
    query_flow_reservation,
    ctx,
):
    """临时用户创建设备预约，管理员审核后用户查询最终状态。"""
    start_time = "10:00"
    end_time = "11:00"
    identity = (
        temp_user_account["id"],
        temp_equipment["lab_id"],
        temp_equipment["id"],
        flow_reservation_date,
        start_time,
        end_time,
    )
    flow_reservation_registry(identity)
    user_reservation_api = api_factory("reservation", role="temp_user")
    admin_reservation_api = api_factory("reservation", role="admin")

    with allure.step("普通用户创建设备预约"):
        assert_common_response(
            user_reservation_api.create(
                {
                    "lab_id": temp_equipment["lab_id"],
                    "equipment_id": temp_equipment["id"],
                    "date": flow_reservation_date,
                    "start_time": start_time,
                    "end_time": end_time,
                    "remark": "Flow预约审核联调",
                }
            ),
            {
                "http_status": 200,
                "code": 200,
                "message": "请求成功",
                "data": None,
            },
        )
        reservation = query_flow_reservation(identity)
        assert reservation is not None, "预约接口成功后未查询到对应预约记录"
        ctx.set_temp("flow_reservation_id", reservation["id"])

    with allure.step("普通用户查询到待审核预约"):
        user_list_body = assert_common_response(
            user_reservation_api.list(
                {"page": 1, "page_size": 100, "status": 0}
            ),
            {"http_status": 200, "code": 200, "message": "请求成功"},
        )
        pending_item = _find_reservation(
            user_list_body["data"]["list"], ctx.get_temp("flow_reservation_id")
        )
        assert pending_item is not None, "用户预约列表中未找到新建预约"
        assert pending_item["user_id"] == temp_user_account["id"]
        assert pending_item["status"] == 0

    with allure.step("管理员查询并审核通过该预约"):
        admin_list_body = assert_common_response(
            admin_reservation_api.list(
                {"page": 1, "page_size": 100, "status": 0}
            ),
            {"http_status": 200, "code": 200, "message": "请求成功"},
        )
        assert _find_reservation(
            admin_list_body["data"]["list"], ctx.get_temp("flow_reservation_id")
        ) is not None, "管理员预约列表中未找到待审核预约"

        assert_common_response(
            admin_reservation_api.audit(
                ctx.get_temp("flow_reservation_id"), {"status": 1}
            ),
            {
                "http_status": 200,
                "code": 200,
                "message": "请求成功",
                "data": None,
            },
        )

    with allure.step("普通用户查询到审核通过后的最终状态"):
        approved_list_body = assert_common_response(
            user_reservation_api.list(
                {"page": 1, "page_size": 100, "status": 1}
            ),
            {"http_status": 200, "code": 200, "message": "请求成功"},
        )
        approved_item = _find_reservation(
            approved_list_body["data"]["list"], ctx.get_temp("flow_reservation_id")
        )
        assert approved_item is not None, "用户预约列表中未找到已通过预约"
        assert approved_item["status"] == 1

        reservation = query_flow_reservation(identity)
        assert reservation["status"] == 1, "审核成功后数据库预约状态未更新"
