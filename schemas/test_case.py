from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    model_validator,
)

TestRole = Literal[
    "anonymous",
    "user",
    "admin",
    "temp_user",
    "temp_admin",
]

DataTypeName = Literal["str", "int", "float", "bool", "dict", "list", "null"]
ResponseType = Literal["json", "binary"]


class ApiResponseContract(BaseModel):
    """后端公共响应结构，用于校验实际响应的基础字段与类型。"""

    model_config = ConfigDict(extra="allow")

    code: StrictInt
    message: StrictStr
    data: Any


class ResponseExpectation(BaseModel):
    """公共响应断言契约，描述状态码以及 data 的通用校验规则。"""

    model_config = ConfigDict(extra="forbid")

    http_status: StrictInt = Field(ge=100, le=599)
    response_type: ResponseType = "json"
    code: StrictInt | None = None
    message: StrictStr | None = None
    data: Any = None
    data_keys: list[StrictStr] = Field(default_factory=list)
    data_fields: dict[str, Any] = Field(default_factory=dict)
    data_types: dict[str, DataTypeName] = Field(default_factory=dict)
    nested_data_keys: dict[str, list[StrictStr]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_data_rules(self):
        """精确 data 断言和局部 data 断言不能同时配置，避免语义冲突。"""
        detail_fields = (
            self.data_keys,
            self.data_fields,
            self.data_types,
            self.nested_data_keys,
        )
        if "data" in self.model_fields_set and any(detail_fields):
            raise ValueError("expect.data 不能与 data_keys/data_fields/data_types/nested_data_keys 同时使用")
        if self.response_type == "json":
            if self.code is None or self.message is None:
                raise ValueError("JSON 响应必须配置 expect.code 和 expect.message")
        elif (
            self.code is not None
            or self.message is not None
            or "data" in self.model_fields_set
            or any(detail_fields)
        ):
            raise ValueError("二进制响应只能配置 http_status 和 response_type")
        return self


class DatabaseExpectation(BaseModel):
    """数据库断言契约，区分普通字段比对与密码哈希验证。"""

    model_config = ConfigDict(extra="forbid")

    fields: dict[str, Any] = Field(default_factory=dict)
    password_plaintext: StrictStr | None = None
    exists: StrictBool | None = None

    @model_validator(mode="after")
    def validate_verification_rule(self):
        """数据库断言至少需要配置一种校验规则。"""
        if not self.fields and self.password_plaintext is None and self.exists is None:
            raise ValueError(
                "db_verify 至少需要配置 fields、password_plaintext 或 exists"
            )
        if self.exists is False and (self.fields or self.password_plaintext is not None):
            raise ValueError("db_verify.exists=false 时不能再校验记录字段或密码")
        return self


class BaseApiCase(BaseModel):
    """接口测试用例公共结构。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: StrictStr = Field(min_length=1)
    role: TestRole = "anonymous"
    payload: dict[str, Any] | None = None
    path_params: dict[str, Any] = Field(default_factory=dict)
    expect: ResponseExpectation
    db_verify: DatabaseExpectation | None = None
