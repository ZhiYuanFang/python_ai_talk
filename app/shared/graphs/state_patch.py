"""
图 State 补丁合并

业务说明：
Pydantic State 上应用节点返回的字段补丁；未出现在补丁中的已有字段必须保留。
供 stream 终态合并与边界 ainvoke 结果合并使用，避免 dict.update 擦掉通道字段。
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Type, TypeVar, get_args, get_origin

from pydantic import BaseModel

T = TypeVar("T")


def state_get(state: Any, key: str, default: Any = None) -> Any:
    """
    从 State 读字段：支持 Pydantic 属性与 dict。

    共享节点用此函数，避免硬依赖某一业务 State 类。
    """
    if state is None:
        return default
    if isinstance(state, Mapping):
        return state.get(key, default)
    return getattr(state, key, default)


def _annotation_model(annotation: Any) -> Optional[Type[BaseModel]]:
    """从字段注解取出内层 BaseModel（含 Optional）。"""
    if annotation is None:
        return None
    origin = get_origin(annotation)
    if origin is not None:
        for arg in get_args(annotation):
            if isinstance(arg, type) and issubclass(arg, BaseModel):
                return arg
        return None
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    return None


def _coerce_value(annotation: Any, value: Any) -> Any:
    """补丁值若对应嵌套模型且给的是 dict，则 model_validate。"""
    if value is None:
        return None
    model_cls = _annotation_model(annotation)
    if model_cls is None:
        return value
    if isinstance(value, model_cls):
        return value
    if isinstance(value, Mapping):
        return model_cls.model_validate(value)
    return value


def apply_state_patch(state: Any, patch: Optional[Mapping[str, Any]]) -> Any:
    """
    将补丁合并进 State，不丢弃补丁未提及的已有字段。

    - Pydantic：model_copy(update=...)，嵌套 dict 按字段类型校验成模型
    - dict：浅拷贝后 update（兼容过渡）
    - 空补丁：原样返回
    """
    if not patch:
        return state
    if isinstance(state, BaseModel):
        update: Dict[str, Any] = {}
        fields = type(state).model_fields
        for key, raw in patch.items():
            if key not in fields:
                # 未声明通道不写入，避免静默污染；调用方应保证字段在 State 上
                continue
            update[key] = _coerce_value(fields[key].annotation, raw)
        return state.model_copy(update=update)
    if isinstance(state, dict):
        merged = dict(state)
        merged.update(dict(patch))
        return merged
    return state


def ensure_model(state: Any, model_cls: Type[T]) -> T:
    """边界：dict 或已是模型 → 指定 Pydantic 类型。"""
    if isinstance(state, model_cls):
        return state
    if isinstance(state, Mapping):
        return model_cls.model_validate(dict(state))  # type: ignore[misc]
    if isinstance(state, BaseModel):
        return model_cls.model_validate(state.model_dump())  # type: ignore[misc]
    raise TypeError(f"无法将 {type(state)} 转为 {model_cls}")
