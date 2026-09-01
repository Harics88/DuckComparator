# Oracle Table Compare

Oracle Table Compare is a normal, non-containerized Python package for Apache Airflow 3. It extracts two Oracle tables in chunks, stages them in a disk-backed DuckDB database, performs a null-safe primary-key comparison, and produces a self-contained HTML dashboard plus an Excel evidence workbook.

Docker is only the local test harness. Production does not require or use Docker.

See the [DuckComparator User Guide](USER_GUIDE.md) for the architecture diagram, full deployment walkthrough, report interpretation, and troubleshooting.

The optional [YAML Registry Editor](tools/yaml-editor/README.md) provides a local browser interface for opening, validating, editing, previewing, and downloading comparison registries without handling Oracle credentials.

## Production installation for Airflow 3

The Airflow workers need Python 3.10 or newer, Oracle network access, and writable disk large enough to stage both source tables for one run.

1. Build and install the package on every Airflow worker:

   ```text
   python -m build
   pip install dist/oracle_table_compare-0.1.0-py3-none-any.whl
   ```

   Installing directly from a controlled checkout with `pip install .` is also supported. Airflow itself can remain platform-managed; the package's optional `airflow` dependency is intended for standalone environment provisioning.

2. Deploy `dags/oracle_table_compare.py` to the Airflow DAGs folder.

3. Deploy the YAML registry to a controlled path readable by workers. It contains connection IDs and comparison rules only—never database credentials.

4. Configure these worker environment variables:

   - `TABLE_COMPARE_CONFIG`: absolute path to the YAML registry.
   - `TABLE_COMPARE_OUTPUT`: durable report storage shared with report users.
   - `TABLE_COMPARE_WORKSPACE`: worker-local writable storage for run-scoped DuckDB files. It defaults to `/tmp/table-compare`.

5. Create each referenced Oracle connection in Airflow. Store host, port, username, and password in the Airflow Connection. Put the Oracle service name in the Connection schema field or in Extra as `{"service_name":"..."}`. A complete `{"dsn":"..."}` in Extra is also supported.

The DAG retrieves connections through the official Airflow 3 SDK. It creates a workspace and report directory per Airflow run, closes DuckDB after use, and removes the successful run's temporary database. Failed-run workspaces remain available for diagnosis.

## Comparison registry

The central registry can define many named comparisons:

```yaml
comparisons:
  customer_master:
    description: Customer master reconciliation
    left:
      connection: oracle_prod
      schema: CRM
      table: CUSTOMER
    right:
      connection: oracle_uat
      schema: CRM
      table: CUSTOMER
    primary_key: [CUSTOMER_ID]
    exclude_columns: [LAST_UPDATED_AT]
    rules:
      trim_strings: true
      case_sensitive: false
      numeric_tolerance: 0.0001
    report:
      detail_row_limit: 500000
```

`primary_key` may be omitted when both Oracle tables declare the same primary key. The DAG discovers the ordered key columns from Oracle metadata and rejects incompatible declarations. Configure the key explicitly for views, undeclared keys, or sources whose key declarations differ. Composite keys are supported.

## Run flow

Trigger the `oracle_table_compare` DAG with this run configuration:

```json
{"comparison_name": "customer_master"}
```

For each run, the task:

1. Loads the named registry entry.
2. Resolves its configured or declared Oracle primary key.
3. Streams both sources in chunks into a run-scoped, disk-backed DuckDB database.
4. Rejects duplicate keys, then performs null-safe row and column comparison.
5. Writes reports under `TABLE_COMPARE_OUTPUT/<comparison_name>/<run_id>/` and returns both report paths through the task result.
6. Deletes the temporary DuckDB database after a successful run.

The HTML report is static, self-contained, responsive, printable, and free of external resources or JavaScript. The Excel workbook contains `Summary`, `Changed columns`, `Left only`, `Right only`, and one sheet per changed column with the primary key, left value, and right value. Evidence sheets honor `detail_row_limit` so Excel remains usable.

## Comparison semantics

- `NULL` equals `NULL`; a null on only one side is different.
- Oracle empty strings arrive as nulls and naturally follow that rule.
- String comparison can trim whitespace and ignore case.
- Numeric comparison can apply a configured absolute tolerance.
- Composite keys use null-safe equality.
- Duplicate primary-key values fail fast because row matching would be ambiguous.
- Empty tables are supported when Oracle supplies their column metadata.
- Only columns present on both sides are compared; key and excluded columns are omitted from value comparison.

The report shows left and right totals, keys present on both sides, changed matched rows, left-only and right-only counts, exact-row match rate, and per-column difference counts. It records connection IDs and table identities, never credentials.

## Local verification with Docker

Docker is used only to provide a reproducible local Python environment:

```text
docker build -t oracle-table-compare .
docker run --rm oracle-table-compare
```

To generate the synthetic preview without Oracle, run `examples/generate_sample_report.py` with the package installed or with `PYTHONPATH=src`. Outputs are written to `outputs/sample`.

The scale smoke test stages and compares two fixed 2-million-row sources in a temporary DuckDB file:

```text
python scripts/scale_smoke.py
```
