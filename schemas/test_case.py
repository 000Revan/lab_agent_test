from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

TestRole = Literal[
    "anonymous",
    "user",
    "admin",
    "temp_user",
    "temp_admin",
]


class ResponseExpectation(BaseModel):
    """接口响应预期。"""

    model_config = ConfigDict(extra="forbid")

    http_status: StrictInt
    code: StrictInt
    message: StrictStr
    data_keys: list[str] | None = None
    data_values: dict[str, Any] | None = None


class BaseApiCase(BaseModel):
    """接口测试用例公共结构。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(min_length=1)
    role: TestRole
    payload: dict[str, Any] | None = None
    expect: ResponseExpectation
