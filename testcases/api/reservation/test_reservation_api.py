# 创建预约、预约列表、取消预约、审核预约接口测试
import allure
import pytest

from utils.assert_util import assert_common_response, assert_database_expectation
from utils.yaml_util import load_data_yaml


reservation_data = load_data_yaml("reservation_data.yaml")

reservation_create_case = (
    reservation_data["reservation_create_success"]
    + reservation_data["reservation_create_fail"]
)
reservation_list_case = reservation_data["reservation_list_success"]
reservation_cancel_case = (
    reservation_data["reservation_cancel_success"]
    + reservation_data["reservation_cancel_fail"]
)
reservation_audit_case = (
    reservation_data["reservation_audit_success"]
    + reservation_data["reservation_audit_fail"]
)

pytestmark = [
    allure.epic("实验室预约系统"),
    allure.feature("预约模块"),
]


def reservation_identity(user_id, payload):
    """从创建预约请求中提取可唯一定位测试记录的业务字段。"""
    return (
        user_id,
        payload.get("lab_id"),
        payload.get("equipment_id"),
        payload.get("date"),
        payload.get("start_time"),
        payload.get("end_time"),
    )


class TestReservationApi:
    @allure.story("创建预约接口")
    @pytest.mark.parametrize(
        "case",
        reservation_create_case,
        ids=[case["title"] for case in reservation_create_case],
    )
    def test_create_reservation(
        self,
        api_factory,
        prepared_accounts,
        resolve_case_references,
        delete_api_reservations,
        query_reservation,
        case,
    ):
        """创建实验室或设备预约，并校验时间和关联资源规则。"""
        resolved_case = resolve_case_references(case)
        payload = resolved_case.get("payload") or {}
        user_id = prepared_accounts["user"]["id"]
        identity = reservation_identity(user_id, payload)

        existing = None
        if all(value is not None for value in identity[0:2] + identity[3:]):
            existing = query_reservation(
                user_id=identity[0],
                lab_id=identity[1],
                equipment_id=identity[2],
                reserve_date=identity[3],
                start_time=identity[4],
                end_time=identity[5],
            )
        if existing is None and all(
            value is not None for value in identity[0:2] + identity[3:]
        ):
            delete_api_reservations(identity)

        reservation_api = api_factory("reservation", role=resolved_case["role"])
        with allure.step("发送创建预约请求"):
            res = reservation_api.create(payload)
        with allure.step("断言创建预约响应"):
            assert_common_response(res, resolved_case["expect"])

        if "db_verify" in resolved_case:
            with allure.step("断言创建后的预约数据库记录"):
                reservation = query_reservation(
                    user_id=identity[0],
                    lab_id=identity[1],
                    equipment_id=identity[2],
                    reserve_date=identity[3],
                    start_time=identity[4],
                    end_time=identity[5],
                )
                assert_database_expectation(
                    reservation,
                    resolved_case["db_verify"],
                )

    @allure.story("查询预约列表接口")
    @pytest.mark.parametrize(
        "case",
        reservation_list_case,
        ids=[case["title"] for case in reservation_list_case],
    )
    def test_list_reservation(
        self,
        api_factory,
        prepared_accounts,
        reservation_list_records,
        case,
    ):
        """校验普通用户数据隔离和管理员全量查看能力。"""
        reservation_api = api_factory("reservation", role=case["role"])
        with allure.step("发送查询预约列表请求"):
            res = reservation_api.list(case.get("payload"))
        with allure.step("断言预约列表响应"):
            body = assert_common_response(res, case["expect"])

        items = body["data"]["list"]
        current_id = reservation_list_records["current"]["id"]
        other_id = reservation_list_records["other"]["id"]
        returned_ids = {item["id"] for item in items}

        with allure.step("断言预约列表的数据权限范围"):
            assert current_id in returned_ids, "预约列表缺少当前用户测试预约"
            if case["role"] == "user":
                current_user_id = prepared_accounts["user"]["id"]
                assert all(item["user_id"] == current_user_id for item in items), (
                    f"普通用户预约列表包含其他用户数据：{items!r}"
                )
                assert other_id not in returned_ids, "普通用户查询到了其他用户预约"
            else:
                assert other_id in returned_ids, "管理员预约列表缺少其他用户预约"

    @allure.story("取消预约接口")
    @pytest.mark.parametrize(
        "case",
        reservation_cancel_case,
        ids=[case["title"] for case in reservation_cancel_case],
    )
    def test_cancel_reservation(
        self,
        api_factory,
        resolve_case_references,
        query_reservation,
        case,
    ):
        """取消预约，并校验预约归属和状态限制。"""
        resolved_case = resolve_case_references(case)
        reservation_id = resolved_case["path_params"]["reservation_id"]
        reservation_api = api_factory("reservation", role=resolved_case["role"])

        with allure.step("发送取消预约请求"):
            res = reservation_api.cancel(reservation_id)
        with allure.step("断言取消预约响应"):
            assert_common_response(res, resolved_case["expect"])

        with allure.step("断言取消后的预约数据库状态"):
            reservation = query_reservation(reservation_id=reservation_id)
            assert_database_expectation(
                reservation,
                resolved_case["db_verify"],
            )

    @allure.story("审核预约接口")
    @pytest.mark.parametrize(
        "case",
        reservation_audit_case,
        ids=[case["title"] for case in reservation_audit_case],
    )
    def test_audit_reservation(
        self,
        api_factory,
        resolve_case_references,
        query_reservation,
        case,
    ):
        """管理员审核预约，并校验角色权限和状态机限制。"""
        resolved_case = resolve_case_references(case)
        reservation_id = resolved_case["path_params"]["reservation_id"]
        reservation_api = api_factory("reservation", role=resolved_case["role"])

        with allure.step("发送审核预约请求"):
            res = reservation_api.audit(
                reservation_id,
                resolved_case.get("payload"),
            )
        with allure.step("断言审核预约响应"):
            assert_common_response(res, resolved_case["expect"])

        with allure.step("断言审核后的预约数据库状态"):
            reservation = query_reservation(reservation_id=reservation_id)
            assert_database_expectation(
                reservation,
                resolved_case["db_verify"],
            )
