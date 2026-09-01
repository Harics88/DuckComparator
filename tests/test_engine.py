import pandas as pd
import pytest

from oracle_table_compare.engine import DuckDBComparator
from oracle_table_compare.models import ComparisonDefinition, Rules, Source


def definition() -> ComparisonDefinition:
    return ComparisonDefinition("customers", Source("left", "CRM", "CUSTOMER"), Source("right", "CRM", "CUSTOMER"), ("ID",))


def test_null_safe_row_and_column_comparison() -> None:
    comparator = DuckDBComparator()
    comparator.load_frames("left_source", [pd.DataFrame({"ID": [1, 2, 3], "NAME": [None, "same", "left"]})])
    comparator.load_frames("right_source", [pd.DataFrame({"ID": [1, 2, 4], "NAME": [None, "changed", "right"]})])
    result = comparator.compare(definition())
    assert result.summary == {"matching": 1, "different": 1, "left_only": 1, "right_only": 1, "left_total": 3, "right_total": 3}
    assert result.changed_columns == {"NAME": 1}
    assert result.column_differences("NAME", 10).to_dict("records") == [{"ID": 2, "left_value": "same", "right_value": "changed"}]
    assert result.left_only(10).to_dict("records") == [{"ID": 3, "NAME": "left"}]
    assert result.right_only(10).to_dict("records") == [{"ID": 4, "NAME": "right"}]


def test_duplicate_keys_are_rejected() -> None:
    comparator = DuckDBComparator()
    comparator.load_frames("left_source", [pd.DataFrame({"ID": [1, 1], "NAME": ["a", "b"]})])
    comparator.load_frames("right_source", [pd.DataFrame({"ID": [1], "NAME": ["a"]})])
    with pytest.raises(ValueError, match="duplicate"):
        comparator.compare(definition())


def test_string_rules_and_numeric_tolerance() -> None:
    comparator = DuckDBComparator()
    comparator.load_frames("left_source", [pd.DataFrame({"ID": [1], "NAME": ["  Ada "], "AMOUNT": [10.0]})])
    comparator.load_frames("right_source", [pd.DataFrame({"ID": [1], "NAME": ["ada"], "AMOUNT": [10.00001]})])
    item = ComparisonDefinition("customers", Source("left", "CRM", "CUSTOMER"), Source("right", "CRM", "CUSTOMER"), ("ID",), rules=Rules(case_sensitive=False, numeric_tolerance=0.001))
    assert comparator.compare(item).summary["matching"] == 1


def test_empty_tables_are_supported() -> None:
    comparator = DuckDBComparator()
    empty = pd.DataFrame({"ID": pd.Series(dtype="int64"), "NAME": pd.Series(dtype="object")})
    comparator.load_frames("left_source", [empty])
    comparator.load_frames("right_source", [empty])
    assert comparator.compare(definition()).summary["left_total"] == 0
