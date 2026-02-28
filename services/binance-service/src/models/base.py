"""
Pydantic模型基类

提供 camelCase/snake_case 自动转换的基类。

设计原则：
- SnakeCaseModel: 用于接收外部输入，自动将camelCase转为snake_case
- CamelCaseModel: 用于响应输出，序列化时自动转为camelCase

引用: docs/backend/design/DATABASE_COORDINATED_ARCHITECTURE.md#44-数据命名规范
"""

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel, to_snake


class SnakeCaseModel(BaseModel):
    """请求模型基类 - 接收 camelCase 自动转为 snake_case

    用于解析币安API响应，自动将camelCase字段转换为snake_case内部字段。
    例如: "priceChange" -> price_change
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
