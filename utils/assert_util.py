from utils.password_util import verify_password


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
    """
    断言响应体包含统一响应字段
    1.断言body字段类型
    2.断言基础结构完整
    """
    assert isinstance(body, dict), f"响应体类型错误，应该为dict，实际为{type(body)}"

    required_keys = ["code", "message", "data"]
    for key in required_keys:
        assert key in body, f"响应体结构错误，缺少'{key}'字段"


def assert_common_response(response, expect):
    """断言通用响应结构"""
    # 断言http状态码
    assert_http_status(response, expect.get("http_status", 200))

    body = response.json()
    # 断言结构完整{code,message,data}
    assert_response_schema(body)
    # 断言响应code正确
    assert_response_code(body, expect["code"])
    # 断言响应message正确
    assert_response_message(body, expect["message"])
    return body


def assert_data_exists(body):
    """断言响应存在 data 字段"""
    assert "data" in body, "响应data错误，'data'字段缺失"
    return body["data"]


def assert_data_key_exists(body, key):
    """断言 data 内单个字段存在"""
    data = assert_data_exists(body)
    assert key in data, f"'data'内部错误，缺少{key}字段"
    return data[key]


def assert_data_keys_exist(body, keys):
    """断言 data 内多个字段存在"""
    data = assert_data_exists(body)
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
    """断言data内特定数据一致"""
    data = assert_data_exists(body)
    for key, value in data_value.items():
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
    """断言数据库记录中密码字段数据一致"""
    assert record is not None, "数据库查询结果为空"
    assert "password" in record, "数据库查询结果缺少字段:password"
    password_hash = record["password"]
    expected_passowrd = expected["password"]

    assert verify_password(
        expected_passowrd, password_hash
    ), "密码修改后数据库字段与预期不一致"
