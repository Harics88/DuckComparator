"""Generate a small report without Oracle, useful for previewing the output."""
from pathlib import Path

import pandas as pd

from oracle_table_compare.engine import DuckDBComparator
from oracle_table_compare.models import ComparisonDefinition, Source
from oracle_table_compare.reporting import write_reports


def main() -> None:
    comparator = DuckDBComparator()
    comparator.load_frames(
        "left_source",
        [
            pd.DataFrame(
                {
                    "CUSTOMER_ID": [1001, 1002, 1003, 1004],
                    "NAME": ["Ada", "Grace", "Linus", None],
                    "STATUS": ["ACTIVE", "ACTIVE", "INACTIVE", "ACTIVE"],
                }
            )
        ],
    )
    comparator.load_frames(
        "right_source",
        [
            pd.DataFrame(
                {
                    "CUSTOMER_ID": [1001, 1002, 1004, 1005],
                    "NAME": ["Ada", "Grace Hopper", None, "Margaret"],
                    "STATUS": ["ACTIVE", "ACTIVE", "INACTIVE", "ACTIVE"],
                }
            )
        ],
    )
    definition = ComparisonDefinition(
        name="customer_master_sample",
        description="Synthetic preview of the Oracle comparison report",
        left=Source("oracle_prod", "CRM", "CUSTOMER"),
        right=Source("oracle_uat", "CRM", "CUSTOMER"),
        primary_key=("CUSTOMER_ID",),
    )
    try:
        html, excel = write_reports(comparator.compare(definition), Path("outputs/sample"))
        print(html)
        print(excel)
    finally:
        comparator.close()


if __name__ == "__main__":
    main()
