# 实验室预约系统接口自动化测试

## 测试数据契约

测试数据统一放在 `data/*.yaml`。每个文件由“测试分组 -> 用例列表”组成，所有用例都必须符合 `schemas/test_case.py` 中的 `BaseApiCase`。

```yaml
update_user_profile:
  - title: "普通用户修改资料成功"
    role: temp_user
    payload:
      name: "修改信息测试"
    path_params: {}
    expect:
      http_status: 200
      code: 200
      message: "请求成功"
      data_keys:
        - id
        - name
      data_fields:
        name: "修改信息测试"
      data_types:
        id: int
        name: str
    db_verify:
      fields:
        name: "修改信息测试"
```

公共用例字段：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `title` | 是 | pytest 和 Allure 展示的用例名称，不能为空 |
| `role` | 否 | 请求身份，默认 `anonymous`；支持 `user`、`admin`、`temp_user`、`temp_admin` |
| `payload` | 否 | 请求体或查询参数；无请求数据时使用 `null` |
| `path_params` | 否 | URL 路径参数或测试上下文占位参数 |
| `expect` | 是 | 公共响应预期 |
| `db_verify` | 否 | 接口成功后的数据库预期 |

## 公共响应契约

实际接口响应必须至少包含以下结构，并符合对应类型：

```json
{
  "code": 200,
  "message": "请求成功",
  "data": {}
}
```

`expect` 支持以下断言规则：

| 字段 | 作用 |
| --- | --- |
| `http_status` | HTTP 状态码，限制为 100～599 |
| `code` | 响应体业务状态码，必须为整数 |
| `message` | 响应消息，必须为字符串 |
| `data` | 对整个 `data` 做精确比较，常用于 `data: null` |
| `data_keys` | 断言 `data` 必须包含指定字段 |
| `data_fields` | 断言 `data` 中指定字段的值 |
| `data_types` | 断言字段类型，支持 `str`、`int`、`float`、`bool`、`dict`、`list`、`null` |
| `nested_data_keys` | 断言嵌套对象包含指定字段，例如 `user: [id, username]` |

`data` 是整体精确断言，不能和其他局部 `data_*` 规则同时使用。响应断言统一调用：

```python
body = assert_common_response(response, case["expect"])
```

## 数据库断言契约

普通字段放在 `db_verify.fields` 中；密码数据库字段是哈希值，必须使用 `password_plaintext` 提供预期明文：

```yaml
db_verify:
  fields:
    name: "修改信息测试"
    status: 1
  password_plaintext: "123456"
```

测试脚本统一调用：

```python
assert_database_expectation(record, case["db_verify"])
```

## 加载和新增用例

使用 `load_data_yaml()` 加载数据时，会逐个验证文件、分组和用例：

```python
user_data = load_data_yaml("user_data.yaml")
update_cases = user_data["user_profile_update_success"]
```

字段拼写错误、必填字段缺失、类型错误或出现未声明字段时，会在测试收集阶段直接报错，并显示：

```text
测试数据契约校验失败：文件名 -> 分组名[用例序号]
```

新增用例时：

1. 在对应 `data/*.yaml` 的业务分组中添加用例。
2. 只使用公共契约已经声明的字段，不在模块内发明 `expected_values`、`user_keys` 等别名。
3. 响应通用校验交给 `assert_common_response()`，测试函数只保留跨请求、上下文关联等业务断言。
4. 需要数据库校验时使用 `db_verify`，密码必须使用 `password_plaintext`。
5. 先执行 `.venv/Scripts/python.exe -m pytest --collect-only -q`，确保数据契约和测试收集通过，再执行接口测试。

`data/user_data_example.yaml` 仅保留为契约示例；用户模块实际执行数据唯一来源是 `data/user_data.yaml`。
