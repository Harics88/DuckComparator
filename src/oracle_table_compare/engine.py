"""Disk-backed, null-safe table comparison implemented in DuckDB."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from .models import ComparisonDefinition


def quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


@dataclass
class ComparisonResult:
    connection: duckdb.DuckDBPyConnection
    definition: ComparisonDefinition
    columns: list[str]
    changed_columns: dict[str, int]
    summary: dict[str, int]

    def left_only(self, limit: int) -> pd.DataFrame:
        return self._only_rows("left_source", "left_only", limit)

    def right_only(self, limit: int) -> pd.DataFrame:
        return self._only_rows("right_source", "right_only", limit)

    def _only_rows(self, table: str, status: str, limit: int) -> pd.DataFrame:
        join = " AND ".join(
            f"s.{quote(key)} IS NOT DISTINCT FROM k.{quote(key)}"
            for key in self.definition.primary_key
        )
        return self.connection.execute(
            f"""SELECT s.* FROM {quote(table)} s
                JOIN comparison_keys k ON {join}
                WHERE k._status = ? LIMIT ?""",
            [status, limit],
        ).fetchdf()

    def column_differences(self, column: str, limit: int) -> pd.DataFrame:
        if column not in self.columns:
            raise KeyError(f"Column '{column}' is not comparable")
        keys = ", ".join(f"l.{quote(key)}" for key in self.definition.primary_key)
        predicates = " AND ".join(f"l.{quote(key)} IS NOT DISTINCT FROM r.{quote(key)}" for key in self.definition.primary_key)
        data_type = {row[0]: row[1] for row in self.connection.execute("DESCRIBE left_source").fetchall()}[column].upper()
        return self.connection.execute(
            f"""SELECT {keys}, l.{quote(column)} AS left_value, r.{quote(column)} AS right_value
                FROM left_source l JOIN right_source r ON {predicates}
                WHERE {DuckDBComparator._different_expression(column, data_type, self.definition)}
                LIMIT ?""",
            [limit],
        ).fetchdf()


class DuckDBComparator:
    """Loads two data sets and exposes one complete, reproducible comparison result."""

    def __init__(self, workspace: str | Path = ":memory:") -> None:
        self.connection = duckdb.connect(str(workspace))

    def close(self) -> None:
        self.connection.close()

    def load_frames(self, table_name: str, frames: Iterable[pd.DataFrame]) -> None:
        created = False
        for frame in frames:
            self.connection.register("_compare_batch", frame)
            if not created:
                self.connection.execute(f"CREATE OR REPLACE TABLE {quote(table_name)} AS SELECT * FROM _compare_batch")
                created = True
            elif not frame.empty:
                self.connection.execute(f"INSERT INTO {quote(table_name)} SELECT * FROM _compare_batch")
            self.connection.unregister("_compare_batch")
        if not created:
            raise ValueError(f"No rows supplied for {table_name}")

    def compare(self, definition: ComparisonDefinition) -> ComparisonResult:
        if not definition.primary_key:
            raise ValueError("A primary key must be configured or discovered before comparison")
        left_columns = [row[0] for row in self.connection.execute("DESCRIBE left_source").fetchall()]
        right_columns = [row[0] for row in self.connection.execute("DESCRIBE right_source").fetchall()]
        key_set = set(definition.primary_key)
        if not (key_set <= set(left_columns) and key_set <= set(right_columns)):
            raise ValueError("Every primary key column must exist in both sources")
        self._assert_unique_keys("left_source", definition.primary_key)
        self._assert_unique_keys("right_source", definition.primary_key)
        columns = [name for name in left_columns if name in right_columns and name not in key_set and name not in definition.exclude_columns]
        types = {row[0]: row[1].upper() for row in self.connection.execute("DESCRIBE left_source").fetchall()}
        join = " AND ".join(f"l.{quote(key)} IS NOT DISTINCT FROM r.{quote(key)}" for key in definition.primary_key)
        changed = " OR ".join(self._different_expression(name, types[name], definition) for name in columns) or "FALSE"
        select_keys = ", ".join(f"COALESCE(l.{quote(key)}, r.{quote(key)}) AS {quote(key)}" for key in definition.primary_key)
        self.connection.execute(
            f"""CREATE OR REPLACE TABLE comparison_keys AS
              SELECT {select_keys},
                CASE WHEN l._left_exists IS NULL THEN 'right_only'
                     WHEN r._right_exists IS NULL THEN 'left_only'
                     WHEN {changed} THEN 'different'
                     ELSE 'matching' END AS _status
              FROM (SELECT *, TRUE AS _left_exists FROM left_source) l
              FULL OUTER JOIN (SELECT *, TRUE AS _right_exists FROM right_source) r ON {join}"""
        )
        raw_counts = dict(self.connection.execute("SELECT _status, COUNT(*) FROM comparison_keys GROUP BY _status").fetchall())
        summary = {kind: int(raw_counts.get(kind, 0)) for kind in ("matching", "different", "left_only", "right_only")}
        summary["left_total"] = summary["matching"] + summary["different"] + summary["left_only"]
        summary["right_total"] = summary["matching"] + summary["different"] + summary["right_only"]
        changed_columns: dict[str, int] = {}
        if columns:
            aggregates = ", ".join(
                f"COUNT(*) FILTER (WHERE {self._different_expression(column, types[column], definition)}) AS {quote(column)}"
                for column in columns
            )
            counts = self.connection.execute(
                f"SELECT {aggregates} FROM left_source l JOIN right_source r ON {join}"
            ).fetchone()
            changed_columns = {
                column: int(count)
                for column, count in zip(columns, counts, strict=True)
                if count
            }
        return ComparisonResult(self.connection, definition, columns, changed_columns, summary)

    def _assert_unique_keys(self, table: str, keys: tuple[str, ...]) -> None:
        names = ", ".join(quote(key) for key in keys)
        duplicate = self.connection.execute(f"SELECT 1 FROM {quote(table)} GROUP BY {names} HAVING COUNT(*) > 1 LIMIT 1").fetchone()
        if duplicate:
            raise ValueError(f"{table} contains duplicate primary-key values; comparison is unsafe")

    @staticmethod
    def _different_expression(column: str, data_type: str, definition: ComparisonDefinition) -> str:
        left, right = f"l.{quote(column)}", f"r.{quote(column)}"
        if definition.rules.numeric_tolerance is not None and any(kind in data_type for kind in ("INT", "DECIMAL", "NUMERIC", "DOUBLE", "FLOAT", "REAL")):
            tolerance = definition.rules.numeric_tolerance
            return f"NOT (({left} IS NULL AND {right} IS NULL) OR ({left} IS NOT NULL AND {right} IS NOT NULL AND ABS({left} - {right}) <= {tolerance}))"
        if any(kind in data_type for kind in ("CHAR", "VARCHAR", "TEXT", "STRING")):
            normalized_left, normalized_right = left, right
            if definition.rules.trim_strings:
                normalized_left, normalized_right = f"TRIM({left})", f"TRIM({right})"
            if not definition.rules.case_sensitive:
                normalized_left, normalized_right = f"LOWER({normalized_left})", f"LOWER({normalized_right})"
            return f"{normalized_left} IS DISTINCT FROM {normalized_right}"
        return f"{left} IS DISTINCT FROM {right}"
