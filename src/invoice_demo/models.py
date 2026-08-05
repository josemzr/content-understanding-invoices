from __future__ import annotations

import dataclasses
import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class ExtractedField:
    value: Any
    confidence: float | None = None
    source: Any = None


@dataclass
class ExtractedDocument:
    document_type: str
    analyzer_id: str
    fields: dict[str, ExtractedField]
    page_range: str | None = None
    confidence: float | None = None


@dataclass
class AnalysisReport:
    provider: str
    analyzer_id: str
    duration_ms: float
    documents: list[ExtractedDocument]
    usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_value(dataclasses.asdict(self))


def _json_value(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _json_value(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (dt.date, dt.time, dt.datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "as_dict"):
        return _json_value(value.as_dict())
    return value


def field_value(field_model: Any) -> Any:
    value_array = getattr(field_model, "value_array", None)
    if value_array is not None:
        return [field_value(item) for item in value_array]

    value_object = getattr(field_model, "value_object", None)
    if value_object is not None:
        return {name: field_value(item) for name, item in value_object.items()}

    for attribute in (
        "value_string",
        "value_date",
        "value_time",
        "value_phone_number",
        "value_number",
        "value_integer",
        "value_boolean",
        "value_selection_mark",
        "value_selection_group",
        "value_signature",
        "value_country_region",
        "value_address",
        "value_json",
    ):
        value = getattr(field_model, attribute, None)
        if value is not None:
            return _json_value(value)

    currency = getattr(field_model, "value_currency", None)
    if currency is not None:
        return _json_value(currency.amount)

    return getattr(field_model, "content", None)


def normalize_field(field_model: Any, *, source: Any = None) -> ExtractedField:
    return ExtractedField(
        value=field_value(field_model),
        confidence=getattr(field_model, "confidence", None),
        source=source if source is not None else getattr(field_model, "source", None),
    )
