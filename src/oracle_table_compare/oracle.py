"""Oracle metadata discovery and chunked extraction."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from typing import Any

import oracledb
import pandas as pd

from .models import ComparisonDefinition, Source


def primary_key_columns(connection: oracledb.Connection, schema: str, table: str) -> list[str]:
    """Return the declared primary-key columns in Oracle constraint order."""
    sql = """
        SELECT acc.column_name
        FROM all_constraints ac
        JOIN all_cons_columns acc
          ON ac.owner = acc.owner AND ac.constraint_name = acc.constraint_name
        WHERE ac.constraint_type = 'P' AND ac.owner = :schema AND ac.table_name = :table
        ORDER BY acc.position
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, schema=schema.upper(), table=table.upper())
        return [row[0] for row in cursor]


def resolve_primary_key(
    definition: ComparisonDefinition,
    left_connection: oracledb.Connection,
    right_connection: oracledb.Connection,
) -> ComparisonDefinition:
    """Use a configured key or require matching declared Oracle primary keys."""
    if definition.primary_key:
        return definition
    left_key = tuple(
        primary_key_columns(
            left_connection, definition.left.schema, definition.left.table
        )
    )
    right_key = tuple(
        primary_key_columns(
            right_connection, definition.right.schema, definition.right.table
        )
    )
    if not left_key:
        raise ValueError(
            f"No primary key is declared for {definition.left.schema}.{definition.left.table}; "
            "set primary_key in YAML"
        )
    if left_key != right_key:
        raise ValueError(
            "The source tables declare different primary keys; set an explicit shared key in YAML"
        )
    return replace(definition, primary_key=left_key)


def read_table_chunks(connection: oracledb.Connection, source: Source, chunk_size: int = 100_000) -> Iterator[pd.DataFrame]:
    """Read a configured Oracle table incrementally, without loading it all into Python memory."""
    sql = f"SELECT * FROM {_quote_identifier(source.schema)}.{_quote_identifier(source.table)}"
    with connection.cursor() as cursor:
        cursor.arraysize = chunk_size
        cursor.execute(sql)
        columns = [item[0] for item in cursor.description]
        yielded = False
        while rows := cursor.fetchmany(chunk_size):
            yielded = True
            yield pd.DataFrame.from_records(rows, columns=columns)
        if not yielded:
            yield pd.DataFrame(columns=columns)


def _quote_identifier(identifier: str) -> str:
    """Quote an Oracle identifier read from controlled configuration."""
    return '"' + identifier.replace('"', '""') + '"'


def connection_from_airflow(connection_id: str) -> Any:
    """Create an Oracle connection from an Airflow connection at task runtime."""
    from airflow.sdk import Connection

    saved = Connection.get(connection_id)
    extras = saved.extra_dejson
    dsn = extras.get("dsn")
    if not dsn:
        if service_name := extras.get("service_name") or saved.schema:
            dsn = oracledb.makedsn(
                saved.host, saved.port or 1521, service_name=service_name
            )
        else:
            raise ValueError(
                f"Airflow connection '{connection_id}' needs a service_name in Extra, "
                "a service name in Schema, or a complete dsn in Extra"
            )
    return oracledb.connect(user=saved.login, password=saved.password, dsn=dsn)
