from pydantic import ValidationError

from schemas.test_case import (
    ApiResponseContract,
    DatabaseExpectation,
    ResponseExpectation,
)
from utils.password_util import verify_password


DATA_TYPE_MAP = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "dict": dict,
    "list": list,
    "null": type(None),
}


class KnownBackendBugAssertionError(AssertionError):
    """仅标识精确命中的已知后端缺陷，避免 xfail 吞掉其他失败。"""


def raise_if_known_bug_response(response, *, http_status, code, message):
    """响应精确命中已知缺陷时抛出专用异常，供严格 xfail 捕获。"""
    if response.status_code != http_status:
        return

    try:
        body = response.json()
    except ValueError:
        return

    if body.get("code") == code and body.get("message") == message:
        raise KnownBackendBugAssertionError(
            f"命中已知后端缺陷：http_status={http_status}, "
            f"code={code}, message={message}"
        )


def assert_http_status(res, expected=200):
    """断言 HTTP 响应码"""
    assert (
        res.status_code == expected
    ), f"HTTP状态码错误，应该为{expected}，实际为{res.status_code}"


def assert_response_code(body, expected=200):
    """断言业务 code"""
    code = body.get("code")
    assert code == expected, f"响应code错误，应该为{expected}，实际为{code}"


def assert_response_message(body, expected):
    """断言响应 message"""
    message = body.get("message")
    assert message == expected, f"响应message错误，应该为{expected}，实际为{message}"


def assert_response_schema(body):
    """使用公共响应契约校验实际响应的字段和类型。"""
    try:
        return ApiResponseContract.model_validate(body)
    except ValidationError as exc:
        raise AssertionError(f"响应体不符合公共响应契约：\n{exc}") from exc


def _parse_response_expectation(expect):
    """把字典或契约对象统一转换为 ResponseExpectation。"""
    if isinstance(expect, ResponseExpectation):
        return expect
    try:
        return ResponseExpectation.model_validate(expect)
    except ValidationError as exc:
        raise AssertionError(f"响应预期不符合测试数据契约：\n{exc}") from exc


def _assert_expected_data(body, expectation):
    """执行公共响应契约中的 data 精确、字段、类型和嵌套字段断言。"""
    if "data" in expectation.model_fields_set:
        assert_data_field_equal(body, expectation.data)
        return

    if expectation.data_keys:
        assert_data_keys_exist(body, expectation.data_keys)

    if expectation.data_fields:
        assert_data_value(body, expectation.data_fields)

    for key, type_name in expectation.data_types.items():
        value = assert_data_key_exists(body, key)
        expected_type = DATA_TYPE_MAP[type_name]
        assert type(value) is expected_type, (
            f"'data'内部数据错误，{key}字段应该为{type_name}类型，"
            f"实际为{type(value).__name__}"
        )

    for parent_key, child_keys in expectation.nested_data_keys.items():
        nested_data = assert_data_key_exists(body, parent_key)
        assert isinstance(nested_data, dict), (
            f"'data.{parent_key}'类型错误，应该为dict，实际为{type(nested_data)}"
        )
        for child_key in child_keys:
            assert child_key in nested_data, (
                f"'data.{parent_key}'内部错误，缺少{child_key}字段"
            )


def assert_common_response(response, expect):
    """按公共响应契约完成 HTTP、JSON 或二进制响应断言。"""
    expectation = _parse_response_expectation(expect)
    assert_http_status(response, expectation.http_status)

    if expectation.response_type == "binary":
        return response.content

    try:
        body = response.json()
    except ValueError as exc:
        raise AssertionError(f"响应体不是合法 JSON：{response.text[:500]}") from exc

    assert_response_schema(body)
    assert_response_code(body, expectation.code)
    assert_response_message(body, expectation.message)
    _assert_expected_data(body, expectation)
    return body


def assert_data_exists(body):
    """断言响应存在 data 字段"""
    assert "data" in body, "响应data错误，'data'字段缺失"
    return body["data"]


def assert_data_key_exists(body, key):
    """断言 data 内单个字段存在"""
    data = assert_data_exists(body)
    assert isinstance(data, dict), f"响应data类型错误，应该为dict，实际为{type(data)}"
    assert key in data, f"'data'内部错误，缺少{key}字段"
    return data[key]


def assert_data_keys_exist(body, keys):
    """断言 data 内多个字段存在"""
    data = assert_data_exists(body)
    assert isinstance(data, dict), f"响应data类型错误，应该为dict，实际为{type(data)}"
    for key in keys:
        assert key in data, f"'data'内部错误，缺少{key}字段"
    return data


def assert_data_field_type(body, key, expected_type):
    """断言 data 内字段类型"""
    value = assert_data_key_exists(body, key)
    assert isinstance(
        value, expected_type
    ), f"'data'内部数据错误，{key}字段应该为{expected_type}类型，实际为{type(value)}"
    return value


def assert_data_value(body, data_value):
    """断言 data 内指定字段值一致。"""
    data = assert_data_exists(body)
    assert isinstance(data, dict), f"响应data类型错误，应该为dict，实际为{type(data)}"
    for key, value in data_value.items():
        assert key in data, f"'data'内部错误，缺少{key}字段"
        assert (
            data[key] == value
        ), f"data内部数据错误，字段{key}的值应该为{value}，实际为{data[key]}"


def assert_data_field_equal(body, expected):
    """断言 data 内数据一致"""
    data = assert_data_exists(body)
    assert data == expected, f"data内部数据错误，应该为{expected}，实际为{data}"


def assert_record_fields_equal(record, expected):
    """断言数据库记录中的指定字段与期望值一致"""
    assert record is not None, "数据库查询结果为空"

    for key, expected_value in expected.items():
        assert key in record, f"数据库查询结果缺少字段：{key}"

        actual_value = record[key]
        assert actual_value == expected_value, (
            f"数据库字段{key}校验失败，"
            f"期望={expected_value!r},实际={actual_value!r}"
        )


def assert_record_password_equal(record, expected):
    """断言数据库密码哈希与预期明文匹配。"""
    assert record is not None, "数据库查询结果为空"
    assert "password" in record, "数据库查询结果缺少字段:password"
    password_hash = record["password"]

    assert verify_password(
        expected, password_hash
    ), "密码修改后数据库字段与预期不一致"


def assert_database_expectation(record, expected):
    """按公共数据库契约执行普通字段与密码哈希断言。"""
    try:
        expectation = (
            expected
            if isinstance(expected, DatabaseExpectation)
            else DatabaseExpectation.model_validate(expected)
        )
    except ValidationError as exc:
        raise AssertionError(f"数据库预期不符合测试数据契约：\n{exc}") from exc

    if expectation.exists is False:
        assert record is None, f"数据库记录应该不存在，实际为{record!r}"
        return
    if expectation.exists is True:
        assert record is not None, "数据库记录应该存在，实际查询结果为空"

    if expectation.fields:
        assert_record_fields_equal(record, expectation.fields)
    if expectation.password_plaintext is not None:
        assert_record_password_equal(record, expectation.password_plaintext)
