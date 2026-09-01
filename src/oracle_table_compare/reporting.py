"""Human-readable HTML and Excel comparison reports."""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from .engine import ComparisonResult


def _sheet_name(column: str, used: set[str]) -> str:
    cleaned = "".join(
        "_" if character in "[]:*?/\\" else character for character in column
    ) or "Column"
    candidate = cleaned[:31]
    suffix = 2
    while candidate.casefold() in used:
        marker = f"_{suffix}"
        candidate = cleaned[: 31 - len(marker)] + marker
        suffix += 1
    used.add(candidate.casefold())
    return candidate


def _text(value: Any) -> str:
    return escape(str(value), quote=True)


def _format_workbook(
    writer: pd.ExcelWriter,
    frames: dict[str, pd.DataFrame],
    state_has_differences: bool,
) -> None:
    workbook = writer.book
    ink = "#25233B"
    indigo = "#3D378A"
    border = "#D9D8E2"
    layer = "#F4F3F8"
    verified = "#147968"
    verified_soft = "#E8F6F2"
    review = "#8A5700"
    review_soft = "#FFF4D9"
    header_format = workbook.add_format(
        {
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": indigo,
            "align": "left",
            "valign": "vcenter",
        }
    )
    number_format = workbook.add_format({"num_format": "#,##0", "font_color": ink})
    cell_format = workbook.add_format(
        {"font_color": ink, "bottom": 1, "bottom_color": border}
    )
    for sheet_name, frame in frames.items():
        worksheet = writer.sheets[sheet_name]
        worksheet.hide_gridlines(2)
        worksheet.freeze_panes(1, 0)
        worksheet.set_row(0, 24, header_format)
        if len(frame.columns):
            worksheet.autofilter(0, 0, len(frame.index), len(frame.columns) - 1)
        for index, column in enumerate(frame.columns):
            samples = [
                str(column),
                *(str(value) for value in frame[column].head(100).dropna()),
            ]
            width = min(max(max(map(len, samples), default=10) + 2, 12), 48)
            is_numeric = pd.api.types.is_numeric_dtype(frame[column])
            worksheet.set_column(
                index, index, width, number_format if is_numeric else cell_format
            )

    summary = writer.sheets["Summary"]
    title_format = workbook.add_format(
        {"bold": True, "font_size": 20, "font_color": ink, "valign": "vcenter"}
    )
    label_format = workbook.add_format(
        {"bold": True, "font_size": 9, "font_color": "#5D5A70", "bg_color": layer}
    )
    value_format = workbook.add_format({"font_color": ink, "bg_color": layer})
    state_format = workbook.add_format(
        {
            "bold": True,
            "font_size": 12,
            "font_color": review if state_has_differences else verified,
            "bg_color": review_soft if state_has_differences else verified_soft,
            "align": "left",
            "valign": "vcenter",
        }
    )
    summary.merge_range("A1:H1", "DuckComparator · Reconciliation Ledger", title_format)
    summary.merge_range(
        "A3:H3",
        "△ DIFFERENCES FOUND — review exception sheets"
        if state_has_differences
        else "✓ MATCH — all compared rows agree",
        state_format,
    )
    summary.set_row(0, 30)
    summary.set_row(2, 26)
    summary.set_row(11, 24, header_format)
    summary.set_column("A:A", 22, label_format)
    summary.set_column("B:G", 22, value_format)
    summary.freeze_panes(12, 0)


def _write_excel(result: ComparisonResult, path: Path) -> None:
    definition = result.definition
    summary = result.summary
    matched_keys = summary["matching"] + summary["different"]
    union_keys = matched_keys + summary["left_only"] + summary["right_only"]
    match_rate = summary["matching"] / union_keys if union_keys else 1.0
    metadata_rows = [
        ("Comparison", definition.name),
        ("Description", definition.description or "—"),
        ("Left source", f"{definition.left.schema}.{definition.left.table}"),
        ("Left connection ID", definition.left.connection),
        ("Right source", f"{definition.right.schema}.{definition.right.table}"),
        ("Right connection ID", definition.right.connection),
        ("Primary key", ", ".join(definition.primary_key)),
    ]
    metric_frame = pd.DataFrame(
        [
            {
                "left_total": summary["left_total"],
                "right_total": summary["right_total"],
                "matched_keys": matched_keys,
                "exact_matches": summary["matching"],
                "changed_rows": summary["different"],
                "left_only": summary["left_only"],
                "right_only": summary["right_only"],
                "exact_match_rate": match_rate,
            }
        ]
    )
    changed_frame = pd.DataFrame(
        [
            {"column": name, "difference_count": count}
            for name, count in result.changed_columns.items()
        ],
        columns=["column", "difference_count"],
    )
    limit = definition.report.detail_row_limit
    frames: dict[str, pd.DataFrame] = {
        "Changed columns": changed_frame,
        "Left only": result.left_only(limit),
        "Right only": result.right_only(limit),
    }
    used_sheets = {"summary", "changed columns", "left only", "right only"}
    for column in result.changed_columns:
        frames[_sheet_name(column, used_sheets)] = result.column_differences(column, limit)

    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        pd.DataFrame([[None] * len(metric_frame.columns)]).to_excel(
            writer, sheet_name="Summary", index=False, header=False
        )
        pd.DataFrame(metadata_rows, columns=["Field", "Value"]).to_excel(
            writer, sheet_name="Summary", index=False, header=False, startrow=4
        )
        metric_frame.to_excel(writer, sheet_name="Summary", index=False, startrow=11)
        for sheet_name, frame in frames.items():
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
        _format_workbook(
            writer,
            {"Summary": metric_frame, **frames},
            state_has_differences=any(
                summary[key] for key in ("different", "left_only", "right_only")
            ),
        )
        summary_sheet = writer.sheets["Summary"]
        percent_format = writer.book.add_format(
            {"num_format": "0.00%", "font_color": "#25233B"}
        )
        summary_sheet.set_column(7, 7, 20, percent_format)
        summary_sheet.write_comment(
            11,
            7,
            "Exact matches divided by all distinct keys across both sources. "
            "Empty-vs-empty is 100%.",
        )


def _metric(label: str, value: str, detail: str = "") -> str:
    detail_html = f"<small>{_text(detail)}</small>" if detail else ""
    return (
        "<div class='metric'>"
        f"<span>{_text(label)}</span><strong>{_text(value)}</strong>{detail_html}"
        "</div>"
    )


def _write_html(result: ComparisonResult, html_path: Path, xlsx_path: Path) -> None:
    definition = result.definition
    summary = result.summary
    changed_rows = summary["different"]
    matched_keys = summary["matching"] + changed_rows
    union_keys = matched_keys + summary["left_only"] + summary["right_only"]
    match_rate = summary["matching"] / union_keys if union_keys else 1.0
    has_differences = any(
        summary[key] for key in ("different", "left_only", "right_only")
    )
    state_class = "review" if has_differences else "match"
    state_symbol = "△" if has_differences else "✓"
    state_label = "DIFFERENCES FOUND" if has_differences else "MATCH"
    state_message = (
        "Exceptions require review in the evidence workbook."
        if has_differences
        else "Every distinct key and compared value agrees across both sources."
    )
    coverage_metrics = "".join(
        [
            _metric("Left rows", f"{summary['left_total']:,}"),
            _metric("Right rows", f"{summary['right_total']:,}"),
            _metric("Matched keys", f"{matched_keys:,}", "Present on both sides"),
            _metric(
                "Exact-row match rate",
                f"{match_rate:.2%}",
                "Exact matches ÷ all distinct keys",
            ),
        ]
    )
    exception_metrics = "".join(
        [
            _metric("Changed matched rows", f"{changed_rows:,}"),
            _metric("Left only", f"{summary['left_only']:,}"),
            _metric("Right only", f"{summary['right_only']:,}"),
        ]
    )
    change_rows = "".join(
        "<tr>"
        f"<td>{_text(column)}</td><td class='number'>{count:,}</td>"
        "</tr>"
        for column, count in result.changed_columns.items()
    )
    if not change_rows:
        change_rows = (
            "<tr><td colspan='2' class='empty'>"
            "✓ No compared columns contain different values."
            "</td></tr>"
        )
    html_path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_text(definition.name)} · DuckComparator</title>
  <style>
    :root {{
      color-scheme: light;
      --indigo: oklch(0.400 0.150 270); --indigo-dark: oklch(0.300 0.120 270);
      --teal: oklch(0.390 0.090 174); --teal-soft: oklch(0.955 0.025 174);
      --amber: oklch(0.420 0.100 72); --amber-soft: oklch(0.960 0.030 82);
      --ink: oklch(0.245 0.025 270); --muted: oklch(0.470 0.025 270);
      --border: oklch(0.875 0.015 270); --surface: oklch(0.985 0.006 270);
      --layer: oklch(0.960 0.012 270); --white: oklch(1 0 0);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; background:var(--surface); color:var(--ink); font:400 15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    main {{ width:min(1120px,calc(100% - 32px)); margin:40px auto 64px; }}
    .ledger {{ background:var(--white); border:1px solid var(--border); border-radius:10px; overflow:hidden; }}
    header {{ padding:28px 32px 24px; border-bottom:1px solid var(--border); }}
    .report-label,.group-title,.source-role,.metric span {{ color:var(--muted); font-size:12px; font-weight:650; letter-spacing:.04em; text-transform:uppercase; }}
    h1 {{ margin:5px 0 4px; font-size:32px; line-height:1.15; letter-spacing:-.025em; text-wrap:balance; }}
    header p {{ margin:0; max-width:70ch; color:var(--muted); text-wrap:pretty; }}
    .key-line {{ margin-top:14px; color:var(--ink); font-size:13px; }} .key-line b {{ color:var(--muted); }}
    .state-band {{ display:flex; align-items:center; justify-content:space-between; gap:20px; padding:20px 32px; border-bottom:1px solid var(--border); }}
    .state-band.match {{ background:var(--teal-soft); color:var(--teal); }} .state-band.review {{ background:var(--amber-soft); color:var(--amber); }}
    .state-copy {{ display:flex; align-items:center; gap:12px; }} .state-symbol {{ font-size:24px; line-height:1; }}
    .state-copy strong {{ display:block; font-size:16px; }} .state-copy span:last-child {{ display:block; color:var(--ink); font-size:13px; }}
    .state-pill {{ border:1px solid currentColor; border-radius:999px; padding:5px 9px; white-space:nowrap; font-size:11px; font-weight:750; letter-spacing:.04em; }}
    .content {{ padding:32px; }}
    .metric-strip {{ display:grid; grid-template-columns:minmax(0,4fr) minmax(0,3fr); border:1px solid var(--border); border-radius:10px; overflow:hidden; }}
    .metric-group {{ background:var(--layer); }} .metric-group + .metric-group {{ border-left:1px solid var(--border); background:var(--white); }}
    .group-title {{ display:block; padding:10px 16px; border-bottom:1px solid var(--border); }}
    .metrics {{ display:flex; min-height:104px; }} .metric {{ flex:1 1 0; min-width:0; padding:16px; }} .metric + .metric {{ border-left:1px solid var(--border); }}
    .metric strong {{ display:block; margin-top:7px; font-size:23px; line-height:1.1; font-variant-numeric:tabular-nums; }}
    .metric small {{ display:block; margin-top:7px; color:var(--muted); font-size:11px; line-height:1.35; }}
    h2 {{ margin:32px 0 12px; font-size:19px; line-height:1.3; letter-spacing:-.01em; }}
    .sources {{ display:grid; grid-template-columns:minmax(0,1fr) auto minmax(0,1fr); align-items:center; border:1px solid var(--border); border-radius:10px; }}
    .source {{ padding:20px; min-width:0; }} .source strong,.source code {{ display:block; overflow-wrap:anywhere; }}
    .source strong {{ margin-top:5px; font-size:17px; }} .source code {{ margin-top:7px; color:var(--muted); font:inherit; }} .source code b {{ color:var(--ink); }}
    .compare-mark {{ color:var(--indigo); font-size:21px; }}
    .table-wrap {{ overflow-x:auto; border:1px solid var(--border); border-radius:10px; }} table {{ width:100%; border-collapse:collapse; }}
    th,td {{ padding:11px 14px; border-bottom:1px solid var(--border); text-align:left; }} th {{ background:var(--layer); color:var(--muted); font-size:12px; letter-spacing:.03em; }}
    tbody tr:last-child td {{ border-bottom:0; }} .number {{ text-align:right; font-variant-numeric:tabular-nums; }} .empty {{ color:var(--teal); text-align:center; padding:24px; }}
    .evidence {{ display:flex; align-items:center; justify-content:space-between; gap:20px; margin-top:24px; padding-top:24px; border-top:1px solid var(--border); }}
    .evidence p {{ margin:0; max-width:65ch; color:var(--muted); font-size:13px; }}
    .report-link {{ display:inline-block; flex:0 0 auto; padding:10px 14px; border-radius:6px; background:var(--indigo); color:var(--white); font-weight:650; text-decoration:none; }}
    .report-link:hover {{ background:var(--indigo-dark); }} .report-link:focus-visible {{ outline:3px solid oklch(0.70 0.10 270); outline-offset:2px; }}
    @media (max-width:820px) {{
      main {{ margin-top:16px; }} header,.content {{ padding:24px 20px; }} .state-band {{ padding:18px 20px; align-items:flex-start; }} .state-pill {{ display:none; }}
      .metric-strip {{ grid-template-columns:1fr; }} .metric-group + .metric-group {{ border-left:0; border-top:1px solid var(--border); }} .metrics {{ flex-wrap:wrap; }}
      .metric {{ flex-basis:50%; }} .metric:nth-child(odd) {{ border-left:0; }} .metric:nth-child(n+3) {{ border-top:1px solid var(--border); }}
      .sources {{ grid-template-columns:1fr; }} .compare-mark {{ padding:0 20px; transform:rotate(90deg); justify-self:start; }} .evidence {{ align-items:flex-start; flex-direction:column; }}
    }}
    @media (max-width:480px) {{ main {{ width:min(100% - 16px,1120px); }} h1 {{ font-size:26px; overflow-wrap:anywhere; }} .metric {{ flex-basis:100%; border-left:0 !important; border-top:1px solid var(--border); }} .metric:first-child {{ border-top:0; }} }}
    @media print {{ @page {{ margin:14mm; }} body {{ background:white; font-size:11px; }} main {{ width:100%; margin:0; }} .ledger {{ border:0; }} .report-link {{ border:1px solid var(--indigo); background:white; color:var(--indigo); }} .table-wrap {{ overflow:visible; }} }}
  </style>
</head>
<body>
  <main>
    <article class="ledger" aria-labelledby="report-title">
      <header><span class="report-label">Oracle table comparison</span><h1 id="report-title">{_text(definition.name)}</h1><p>{_text(definition.description or 'Comparison report')}</p><div class="key-line"><b>Primary key:</b> {_text(', '.join(definition.primary_key))}</div></header>
      <section class="state-band {state_class}" aria-label="Comparison state: {state_label}"><div class="state-copy"><span class="state-symbol" aria-hidden="true">{state_symbol}</span><div><strong>{state_label}</strong><span>{_text(state_message)}</span></div></div><span class="state-pill">{state_symbol} {state_label}</span></section>
      <div class="content">
        <section class="metric-strip" aria-label="Comparison metrics"><div class="metric-group"><span class="group-title">Row coverage</span><div class="metrics">{coverage_metrics}</div></div><div class="metric-group"><span class="group-title">Exceptions</span><div class="metrics">{exception_metrics}</div></div></section>
        <h2>Compared sources</h2>
        <section class="sources" aria-label="Compared Oracle sources"><div class="source"><span class="source-role">Left source</span><strong>{_text(definition.left.schema)}.{_text(definition.left.table)}</strong><code>Airflow connection ID · <b>{_text(definition.left.connection)}</b></code></div><span class="compare-mark" aria-hidden="true">↔</span><div class="source"><span class="source-role">Right source</span><strong>{_text(definition.right.schema)}.{_text(definition.right.table)}</strong><code>Airflow connection ID · <b>{_text(definition.right.connection)}</b></code></div></section>
        <h2>Changed columns</h2>
        <div class="table-wrap"><table><thead><tr><th scope="col">Column</th><th scope="col" class="number">Rows different</th></tr></thead><tbody>{change_rows}</tbody></table></div>
        <section class="evidence" aria-label="Detailed evidence"><p>Excel includes Summary, Left only, Right only, Changed columns, and one evidence sheet per changed column. Detail sheets are capped at {definition.report.detail_row_limit:,} rows.</p><a class="report-link" href="{_text(xlsx_path.name)}" download>Download Excel evidence</a></section>
      </div>
    </article>
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )


def write_reports(result: ComparisonResult, output_dir: str | Path) -> tuple[Path, Path]:
    """Write a state-forward HTML dashboard and capped Excel evidence workbook."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    html_path = output / f"{result.definition.name}.html"
    xlsx_path = output / f"{result.definition.name}.xlsx"
    _write_excel(result, xlsx_path)
    _write_html(result, html_path, xlsx_path)
    return html_path, xlsx_path
