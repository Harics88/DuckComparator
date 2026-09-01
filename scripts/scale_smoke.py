"""Two-million-row disk-backed comparison smoke test."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from time import monotonic

import numpy as np
import pandas as pd

from oracle_table_compare.engine import DuckDBComparator
from oracle_table_compare.models import ComparisonDefinition, Source

ROW_COUNT = 2_000_000
CHUNK_SIZE = 100_000
CHANGED_ID = ROW_COUNT // 2


def frames(start: int, stop: int, *, mutate: bool = False) -> Iterator[pd.DataFrame]:
    for chunk_start in range(start, stop, CHUNK_SIZE):
        ids = np.arange(chunk_start, min(chunk_start + CHUNK_SIZE, stop), dtype=np.int64)
        values = ids % 1000
        if mutate and CHANGED_ID in ids:
            values = values.copy()
            values[ids == CHANGED_ID] += 1
        yield pd.DataFrame({"ID": ids, "VALUE": values})


def main() -> None:
    workspace = Path("/tmp/duck-comparator-scale.duckdb")
    comparator = DuckDBComparator(workspace)
    started = monotonic()
    try:
        comparator.load_frames("left_source", frames(0, ROW_COUNT))
        comparator.load_frames("right_source", frames(1, ROW_COUNT + 1, mutate=True))
        definition = ComparisonDefinition(
            "scale_smoke",
            Source("left", "TEST", "LARGE_TABLE"),
            Source("right", "TEST", "LARGE_TABLE"),
            ("ID",),
        )
        result = comparator.compare(definition)
        expected = {
            "matching": ROW_COUNT - 2,
            "different": 1,
            "left_only": 1,
            "right_only": 1,
            "left_total": ROW_COUNT,
            "right_total": ROW_COUNT,
        }
        assert result.summary == expected, result.summary
        assert result.changed_columns == {"VALUE": 1}, result.changed_columns
        print(f"2M-row smoke test passed in {monotonic() - started:.2f}s: {result.summary}")
    finally:
        comparator.close()


if __name__ == "__main__":
    main()
