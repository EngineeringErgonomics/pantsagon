from __future__ import annotations

from typing import TypeAlias, TypeGuard

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | dict[str, "JsonValue"] | list["JsonValue"]
JsonDict: TypeAlias = dict[str, JsonValue]
JsonList: TypeAlias = list[JsonValue]


def _is_dict(value: object) -> TypeGuard[dict[object, object]]:
    return isinstance(value, dict)


def _is_list(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


def as_dict(value: object) -> JsonDict:
    return as_json_dict(value)


def as_list(value: object) -> list[JsonValue]:
    return as_json_list(value)


def coerce_json_value(value: object) -> JsonValue:
    if _is_dict(value):
        return {str(k): coerce_json_value(v) for k, v in value.items()}
    if _is_list(value):
        return [coerce_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def as_json_dict(value: object) -> JsonDict:
    if not _is_dict(value):
        return {}
    return {str(k): coerce_json_value(v) for k, v in value.items()}


def as_json_list(value: object) -> list[JsonValue]:
    if not _is_list(value):
        return []
    return [coerce_json_value(item) for item in value]
