# 设备列表、新增、修改、删除接口测试
import allure
import pytest

from utils.assert_util import (
    KnownBackendBugAssertionError,
    assert_common_response,
    assert_database_expectation,
    raise_if_known_bug_response,
)
from utils.yaml_util import load_data_yaml


equipment_data = load_data_yaml("equipment_data.yaml")

equipment_list_case = (
    equipment_data["equipment_list_success"]
    + equipment_data["equipment_list_fail"]
)
equipment_create_case = (
    equipment_data["equipment_create_success"]
    + equipment_data["equipment_create_fail"]
)
equipment_create_known_bug_case = equipment_data["equipment_create_known_bug"]
equipment_update_case = (
    equipment_data["equipment_update_success"]
    + equipment_data["equipment_update_fail"]
)
equipment_delete_case = (
    equipment_data["equipment_delete_success"]
    + equipment_data["equipment_delete_fail"]
)

pytestmark = [
    allure.epic("实验室预约系统"),
    allure.feature("设备模块"),
]


def assert_equipment_list_filter(body, params):
    """断言设备列表的实验室和关键词过滤实际生效。"""
    items = body["data"]["list"]

    if "lab_id" in params:
        assert items, "按实验室查询设备时，返回列表不应为空"
        assert all(item["lab_id"] == params["lab_id"] for item in items), (
            f"设备实验室过滤失败，期望所有记录lab_id={params['lab_id']}，实际={items!r}"
        )

    if "keywords" in params:
        keywords = params["keywords"]
        assert items, "按关键词查询设备时，返回列表不应为空"
        assert all(keywords.lower() in item["name"].lower() for item in items), (
            f"设备关键词过滤失败，keywords={keywords!r}，实际={items!r}"
        )


class TestEquipmentApi:
    @allure.story("查询设备列表接口")
    @pytest.mark.parametrize(
        "case",
        equipment_list_case,
        ids=[case["title"] for case in equipment_list_case],
    )
    def test_list_equipment(self, api_factory, resolve_case_references, case):
        """查询设备列表，并校验分页结构及过滤条件。"""
        resolved_case = resolve_case_references(case)
        params = resolved_case.get("payload") or {}
        equipment_api = api_factory("equipment", role=resolved_case["role"])

        with allure.step("发送查询设备列表请求"):
            res = equipment_api.list(params)
        with allure.step("断言设备列表响应"):
            body = assert_common_response(res, resolved_case["expect"])

        if resolved_case["role"] != "anonymous":
            with allure.step("断言设备列表过滤结果"):
                assert_equipment_list_filter(body, params)

    @allure.story("创建设备接口")
    @pytest.mark.parametrize(
        "case",
        equipment_create_case,
        ids=[case["title"] for case in equipment_create_case],
    )
    def test_create_equipment(
        self,
        api_factory,
        resolve_case_references,
        delete_test_equipment_by_identity,
        query_equipment,
        case,
    ):
        """管理员创建设备及角色权限、关联实验室校验。"""
        resolved_case = resolve_case_references(case)
        payload = resolved_case.get("payload") or {}
        lab_id = payload.get("lab_id")
        name = payload.get("name")

        if (
            lab_id is not None
            and name
            and query_equipment(lab_id=lab_id, name=name) is None
        ):
            delete_test_equipment_by_identity(lab_id, name)

        equipment_api = api_factory("equipment", role=resolved_case["role"])
        with allure.step("发送创建设备请求"):
            res = equipment_api.create(payload)
        with allure.step("断言创建设备响应"):
            assert_common_response(res, resolved_case["expect"])

        if "db_verify" in resolved_case:
            with allure.step("断言创建后的数据库记录"):
                equipment = query_equipment(lab_id=lab_id, name=name)
                assert_database_expectation(
                    equipment,
                    resolved_case["db_verify"],
                )

    @allure.story("创建设备接口")
    @pytest.mark.xfail(
        strict=True,
        raises=KnownBackendBugAssertionError,
        reason=(
            "BUG-EQUIPMENT-001：创建设备未校验lab_id，"
            "数据库外键异常导致HTTP 500"
        ),
    )
    @pytest.mark.parametrize(
        "case",
        equipment_create_known_bug_case,
        ids=[case["title"] for case in equipment_create_known_bug_case],
    )
    def test_create_equipment_known_bug(
        self,
        api_factory,
        resolve_case_references,
        delete_test_equipment_by_identity,
        query_equipment,
        case,
    ):
        """不存在的实验室应返回可预期的业务错误，且不能产生设备记录。"""
        allure.dynamic.title(case["title"])
        resolved_case = resolve_case_references(case)
        payload = resolved_case["payload"]
        lab_id = payload["lab_id"]
        name = payload["name"]
        delete_test_equipment_by_identity(lab_id, name)

        equipment_api = api_factory("equipment", role=resolved_case["role"])
        with allure.step("发送不存在实验室的创建设备请求"):
            res = equipment_api.create(payload)

        raise_if_known_bug_response(
            res,
            http_status=500,
            code=500,
            message="服务器内部错误",
        )

        with allure.step("断言期望的正确响应"):
            assert_common_response(res, resolved_case["expect"])
        with allure.step("断言数据库未产生设备记录"):
            equipment = query_equipment(lab_id=lab_id, name=name)
            assert_database_expectation(equipment, resolved_case["db_verify"])

    @allure.story("修改设备接口")
    @pytest.mark.parametrize(
        "case",
        equipment_update_case,
        ids=[case["title"] for case in equipment_update_case],
    )
    def test_update_equipment(
        self,
        api_factory,
        resolve_case_references,
        query_equipment,
        case,
    ):
        """管理员修改设备及角色权限校验。"""
        resolved_case = resolve_case_references(case)
        equipment_id = resolved_case["path_params"]["equipment_id"]
        equipment_api = api_factory("equipment", role=resolved_case["role"])

        with allure.step("发送修改设备请求"):
            res = equipment_api.update(
                equipment_id,
                resolved_case.get("payload"),
            )
        with allure.step("断言修改设备响应"):
            assert_common_response(res, resolved_case["expect"])

        if "db_verify" in resolved_case:
            with allure.step("断言修改后的数据库记录"):
                equipment = query_equipment(equipment_id=equipment_id)
                assert_database_expectation(
                    equipment,
                    resolved_case["db_verify"],
                )

    @allure.story("删除设备接口")
    @pytest.mark.parametrize(
        "case",
        equipment_delete_case,
        ids=[case["title"] for case in equipment_delete_case],
    )
    def test_delete_equipment(
        self,
        api_factory,
        resolve_case_references,
        query_equipment,
        case,
    ):
        """管理员删除设备及角色权限校验。"""
        resolved_case = resolve_case_references(case)
        equipment_id = resolved_case["path_params"]["equipment_id"]
        equipment_api = api_factory("equipment", role=resolved_case["role"])

        with allure.step("发送删除设备请求"):
            res = equipment_api.delete(equipment_id)
        with allure.step("断言删除设备响应"):
            assert_common_response(res, resolved_case["expect"])

        if "db_verify" in resolved_case:
            with allure.step("断言删除后的数据库记录"):
                equipment = query_equipment(equipment_id=equipment_id)
                assert_database_expectation(
                    equipment,
                    resolved_case["db_verify"],
                )
