from __future__ import annotations

import re
from pathlib import Path

import yaml

from .models import ComparisonDefinition


def load_comparison(path: str | Path, name: str) -> ComparisonDefinition:
    """Connection fields are Airflow connection IDs, never secrets."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise ValueError("Comparison names may contain only letters, numbers, dot, dash, and underscore")
    with Path(path).open(encoding="utf-8") as stream:
        content = yaml.safe_load(stream) or {}
    try:
        return ComparisonDefinition.from_dict(name, content["comparisons"][name])
    except KeyError as exc:
        raise KeyError(f"No comparison named '{name}' in {path}") from exc
