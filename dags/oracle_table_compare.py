"""Airflow 3 DAG: trigger with {\"comparison_name\": \"customer_master\"}."""
from __future__ import annotations

import os
import re
from pathlib import Path

from airflow.sdk import dag, get_current_context, task
from pendulum import datetime


@dag(schedule=None, start_date=datetime(2025, 1, 1, tz="UTC"), catchup=False, tags=["oracle", "reconciliation"])
def oracle_table_compare():
    @task
    def compare(comparison_name: str) -> dict[str, str]:
        from oracle_table_compare.engine import DuckDBComparator
        from oracle_table_compare.oracle import (
            connection_from_airflow,
            read_table_chunks,
            resolve_primary_key,
        )
        from oracle_table_compare.registry import load_comparison
        from oracle_table_compare.reporting import write_reports

        definition = load_comparison(os.environ["TABLE_COMPARE_CONFIG"], comparison_name)
        run_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(get_current_context()["run_id"]))
        workspace_root = Path(os.environ.get("TABLE_COMPARE_WORKSPACE", "/tmp/table-compare"))
        workspace = workspace_root / comparison_name / run_id / "comparison.duckdb"
        workspace.parent.mkdir(parents=True, exist_ok=True)
        comparator = DuckDBComparator(workspace)
        succeeded = False
        try:
            with connection_from_airflow(definition.left.connection) as left, connection_from_airflow(definition.right.connection) as right:
                definition = resolve_primary_key(definition, left, right)
                comparator.load_frames("left_source", read_table_chunks(left, definition.left))
                comparator.load_frames("right_source", read_table_chunks(right, definition.right))
            result = comparator.compare(definition)
            report_directory = Path(os.environ["TABLE_COMPARE_OUTPUT"]) / comparison_name / run_id
            html, xlsx = write_reports(result, report_directory)
            succeeded = True
            return {"html_report": str(html), "excel_report": str(xlsx)}
        finally:
            comparator.close()
            if succeeded:
                workspace.unlink(missing_ok=True)

    compare("{{ dag_run.conf['comparison_name'] }}")


oracle_table_compare()
