"""
Pydantic模型基类

提供 camelCase/snake_case 自动转换的基类。

设计原则：
- CamelCaseModel: 用于API响应，序列化时自动转为 camelCase
- SnakeCaseModel: 用于接收外部输入（如API请求），自动将 camelCase 转为 snake_case

引用: docs/backend/design/DATABASE_COORDINATED_ARCHITECTURE.md#44-数据命名规范
"""

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel, to_snake


class CamelCaseModel(BaseModel):
    """响应模型基类 - 序列化时自动转为 camelCase

    用于API响应消息，内部使用snake_case，序列化输出camelCase。
    例如: internal_field -> "internalField"
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    def model_dump(self, **kwargs):
        """序列化时默认使用 camelCase"""
        kwargs.setdefault("by_alias", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs):
        """JSON序列化时默认使用 camelCase"""
        kwargs.setdefault("by_alias", True)
        return super().model_dump_json(**kwargs)


class SnakeCaseModel(BaseModel):
    """请求模型基类 - 接收 camelCase 自动转为 snake_case

    用于接收外部输入（如WebSocket请求、API请求），自动将camelCase转为snake_case。
    例如: "internalField" -> internal_field

    使用 model_validator 在解析前将所有 camelCase 键转换为 snake_case。
    """

    model_config = ConfigDict(
        alias_generator=to_snake,
        populate_by_name=True,
    )

    @model_validator(mode="before")
    @classmethod
    def convert_camel_to_snake(cls, data):
        """将输入的 camelCase 键转换为 snake_case"""
        if isinstance(data, dict):
            return {to_snake(k): v for k, v in data.items()}
        return data
