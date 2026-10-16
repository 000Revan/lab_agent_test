# 实验室列表、详情、新增、修改、删除接口测试
import allure
import pytest

from utils.assert_util import assert_common_response, assert_database_expectation
from utils.yaml_util import load_data_yaml


lab_data = load_data_yaml("lab_data.yaml")

lab_list_case = lab_data["lab_list_success"] + lab_data["lab_list_fail"]
lab_detail_case = lab_data["lab_detail_success"] + lab_data["lab_detail_fail"]
lab_create_case = lab_data["lab_create_success"] + lab_data["lab_create_fail"]
lab_update_case = lab_data["lab_update_success"] + lab_data["lab_update_fail"]
lab_delete_case = lab_data["lab_delete_success"] + lab_data["lab_delete_fail"]

pytestmark = [
    allure.epic("实验室预约系统"),
    allure.feature("实验室模块"),
]


def assert_lab_list_filter(body, params):
    """断言实验室列表中的状态过滤和关键词过滤实际生效。"""
    items = body["data"]["list"]

    if "status" in params:
        assert items, "按状态查询实验室时，返回列表不应为空"
        assert all(item["status"] == params["status"] for item in items), (
            f"实验室状态过滤失败，期望所有记录status={params['status']}，实际={items!r}"
        )

    if "keywords" in params:
        keywords = params["keywords"]
        assert items, "按关键词查询实验室时，返回列表不应为空"
        assert all(
            keywords in (item.get("name") or "")
            or keywords in (item.get("location") or "")
            for item in items
        ), f"实验室关键词过滤失败，keywords={keywords!r}，实际={items!r}"


class TestLabApi:
    @allure.story("查询实验室列表接口")
    @pytest.mark.parametrize(
        "case",
        lab_list_case,
        ids=[case["title"] for case in lab_list_case],
    )
    def test_list_lab(self, api_factory, resolve_case_references, temp_lab, case):
        """查询实验室列表，并校验分页结构及过滤条件。"""
        resolved_case = resolve_case_references(case)
        params = resolved_case.get("payload") or {}
        lab_api = api_factory("lab", role=resolved_case["role"])

        with allure.step("发送查询实验室列表请求"):
            res = lab_api.list_lab(params)
        with allure.step("断言实验室列表响应"):
            body = assert_common_response(res, resolved_case["expect"])

        if resolved_case["role"] != "anonymous":
            with allure.step("断言实验室列表过滤结果"):
                assert_lab_list_filter(body, params)

    @allure.story("查询实验室详情接口")
    @pytest.mark.parametrize(
        "case",
        lab_detail_case,
        ids=[case["title"] for case in lab_detail_case],
    )
    def test_lab_detail(self, api_factory, resolve_case_references, case):
        """根据实验室 ID 查询详情。"""
        resolved_case = resolve_case_references(case)
        lab_id = resolved_case["path_params"]["lab_id"]
        lab_api = api_factory("lab", role=resolved_case["role"])

        with allure.step("发送查询实验室详情请求"):
            res = lab_api.detail(lab_id)
        with allure.step("断言实验室详情响应"):
            assert_common_response(res, resolved_case["expect"])

    @allure.story("创建实验室接口")
    @pytest.mark.parametrize(
        "case",
        lab_create_case,
        ids=[case["title"] for case in lab_create_case],
    )
    def test_create_lab(
        self,
        api_factory,
        resolve_case_references,
        delete_test_lab_by_name,
        query_lab,
        case,
    ):
        """管理员创建实验室及角色权限校验。"""
        resolved_case = resolve_case_references(case)
        payload = resolved_case.get("payload") or {}
        name = payload.get("name")
        if name and query_lab(name=name) is None:
            delete_test_lab_by_name(name)

        lab_api = api_factory("lab", role=resolved_case["role"])
        with allure.step("发送创建实验室请求"):
            res = lab_api.create(payload)
        with allure.step("断言创建实验室响应"):
            assert_common_response(res, resolved_case["expect"])

        if "db_verify" in resolved_case:
            with allure.step("断言创建后的数据库记录"):
                lab = query_lab(name=name)
                assert_database_expectation(lab, resolved_case["db_verify"])

    @allure.story("修改实验室接口")
    @pytest.mark.parametrize(
        "case",
        lab_update_case,
        ids=[case["title"] for case in lab_update_case],
    )
    def test_update_lab(
        self,
        api_factory,
        resolve_case_references,
        query_lab,
        case,
    ):
        """管理员修改实验室及角色权限校验。"""
        resolved_case = resolve_case_references(case)
        lab_id = resolved_case["path_params"]["lab_id"]
        lab_api = api_factory("lab", role=resolved_case["role"])

        with allure.step("发送修改实验室请求"):
            res = lab_api.update(lab_id, resolved_case.get("payload"))
        with allure.step("断言修改实验室响应"):
            assert_common_response(res, resolved_case["expect"])

        if "db_verify" in resolved_case:
            with allure.step("断言修改后的数据库记录"):
                lab = query_lab(lab_id=lab_id)
                assert_database_expectation(lab, resolved_case["db_verify"])

    @allure.story("删除实验室接口")
    @pytest.mark.parametrize(
        "case",
        lab_delete_case,
        ids=[case["title"] for case in lab_delete_case],
    )
    def test_delete_lab(
        self,
        api_factory,
        resolve_case_references,
        query_lab,
        case,
    ):
        """管理员删除实验室及角色权限校验。"""
        resolved_case = resolve_case_references(case)
        lab_id = resolved_case["path_params"]["lab_id"]
        lab_api = api_factory("lab", role=resolved_case["role"])

        with allure.step("发送删除实验室请求"):
            res = lab_api.delete(lab_id)
        with allure.step("断言删除实验室响应"):
            assert_common_response(res, resolved_case["expect"])

        if "db_verify" in resolved_case:
            with allure.step("断言删除后的数据库记录"):
                lab = query_lab(lab_id=lab_id)
                assert_database_expectation(lab, resolved_case["db_verify"])
