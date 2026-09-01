from zipfile import ZipFile

import pandas as pd

from oracle_table_compare.engine import DuckDBComparator
from oracle_table_compare.models import ComparisonDefinition, Source
from oracle_table_compare.reporting import write_reports


def test_writes_html_and_excel_with_column_detail(tmp_path) -> None:
    comparator = DuckDBComparator()
    comparator.load_frames("left_source", [pd.DataFrame({"ID": [1], "NAME": ["left"]})])
    comparator.load_frames("right_source", [pd.DataFrame({"ID": [1], "NAME": ["right"]})])
    definition = ComparisonDefinition("customers", Source("left", "CRM", "CUSTOMER"), Source("right", "CRM", "CUSTOMER"), ("ID",))
    html, excel = write_reports(comparator.compare(definition), tmp_path)
    assert html.exists() and "Changed columns" in html.read_text(encoding="utf-8")
    assert excel.exists() and excel.stat().st_size > 0
    with ZipFile(excel) as workbook:
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
    for sheet_name in ("Summary", "Changed columns", "Left only", "Right only", "NAME"):
        assert f'name="{sheet_name}"' in workbook_xml


def test_html_exposes_difference_state_sources_and_derived_metrics(tmp_path) -> None:
    comparator = DuckDBComparator()
    comparator.load_frames(
        "left_source", [pd.DataFrame({"ID": [1, 2], "NAME": ["same", "left"]})]
    )
    comparator.load_frames(
        "right_source", [pd.DataFrame({"ID": [1, 2], "NAME": ["same", "right"]})]
    )
    definition = ComparisonDefinition(
        "customers",
        Source("oracle_prod", "CRM", "CUSTOMER"),
        Source("oracle_uat", "CRM", "CUSTOMER"),
        ("ID",),
    )
    html, _ = write_reports(comparator.compare(definition), tmp_path)
    content = html.read_text(encoding="utf-8")
    assert "DIFFERENCES FOUND" in content
    assert "Matched keys</span><strong>2" in content
    assert "Exact-row match rate</span><strong>50.00%" in content
    assert "CRM.CUSTOMER" in content
    assert "oracle_prod" in content and "oracle_uat" in content


def test_html_match_state_and_escapes_metadata(tmp_path) -> None:
    comparator = DuckDBComparator()
    frame = pd.DataFrame({"ID": [1], "VALUE": ["same"]})
    comparator.load_frames("left_source", [frame])
    comparator.load_frames("right_source", [frame])
    definition = ComparisonDefinition(
        "safe_name",
        Source('left<&"', "CRM<", "CUSTOMER"),
        Source("right&", "CRM", "CUSTOMER"),
        ("ID",),
        description="Trusted <script>alert('no')</script> & report",
    )
    html, _ = write_reports(comparator.compare(definition), tmp_path)
    content = html.read_text(encoding="utf-8")
    assert "Comparison state: MATCH" in content
    assert "DIFFERENCES FOUND" not in content
    assert "&lt;script&gt;" in content and "<script>" not in content
    assert "left&lt;&amp;&quot;" in content
    assert "CRM&lt;.CUSTOMER" in content
