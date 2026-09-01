from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Source:
    connection: str
    schema: str
    table: str

@dataclass(frozen=True)
class Rules:
    trim_strings: bool = True
    case_sensitive: bool = True
    numeric_tolerance: float | None = None

@dataclass(frozen=True)
class ReportOptions:
    detail_row_limit: int = 500_000

@dataclass(frozen=True)
class ComparisonDefinition:
    name: str
    left: Source
    right: Source
    primary_key: tuple[str, ...]
    description: str = ""
    exclude_columns: tuple[str, ...] = ()
    rules: Rules = field(default_factory=Rules)
    report: ReportOptions = field(default_factory=ReportOptions)

    @classmethod
    def from_dict(cls, name: str, value: dict[str, Any]) -> ComparisonDefinition:
        def source(key: str) -> Source:
            data = value[key]
            return Source(data["connection"], data["schema"], data["table"])
        keys = tuple(value.get("primary_key", ()))
        return cls(name=name, description=value.get("description", ""), left=source("left"), right=source("right"), primary_key=keys, exclude_columns=tuple(value.get("exclude_columns", ())), rules=Rules(**value.get("rules", {})), report=ReportOptions(**value.get("report", {})))
