import sys
from types import ModuleType, SimpleNamespace
from typing import ClassVar

from oracle_table_compare.models import ComparisonDefinition, Source
from oracle_table_compare.oracle import (
    connection_from_airflow,
    read_table_chunks,
    resolve_primary_key,
)


class FakeCursor:
    def __init__(self, columns):
        self.columns = columns

    def execute(self, *_args, **_kwargs):
        return None

    def __iter__(self):
        return iter((column,) for column in self.columns)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class FakeConnection:
    def __init__(self, columns):
        self.columns = columns

    def cursor(self):
        return FakeCursor(self.columns)


def test_resolves_matching_oracle_primary_keys() -> None:
    definition = ComparisonDefinition(
        "customers",
        Source("left", "CRM", "CUSTOMER"),
        Source("right", "CRM", "CUSTOMER"),
        (),
    )
    resolved = resolve_primary_key(
        definition, FakeConnection(["CUSTOMER_ID"]), FakeConnection(["CUSTOMER_ID"])
    )
    assert resolved.primary_key == ("CUSTOMER_ID",)


class EmptyDataCursor:
    arraysize = 1
    description: ClassVar[list[tuple[str]]] = [("ID",), ("NAME",)]

    def execute(self, _sql):
        return None

    def fetchmany(self, _size):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class EmptyDataConnection:
    def cursor(self):
        return EmptyDataCursor()


def test_empty_oracle_table_yields_schema_frame() -> None:
    source = Source("connection", "CRM", "CUSTOMER")
    frames = list(read_table_chunks(EmptyDataConnection(), source))
    assert len(frames) == 1
    assert frames[0].empty
    assert list(frames[0].columns) == ["ID", "NAME"]


def test_uses_airflow_3_sdk_connection(monkeypatch) -> None:
    saved = SimpleNamespace(
        extra_dejson={"service_name": "FREEPDB1"},
        schema=None,
        host="oracle.example",
        port=1521,
        login="reader",
        password="secret",
    )

    class SDKConnection:
        @classmethod
        def get(cls, connection_id):
            assert connection_id == "oracle_prod"
            return saved

    airflow = ModuleType("airflow")
    sdk = ModuleType("airflow.sdk")
    sdk.Connection = SDKConnection
    monkeypatch.setitem(sys.modules, "airflow", airflow)
    monkeypatch.setitem(sys.modules, "airflow.sdk", sdk)
    monkeypatch.setattr(
        "oracle_table_compare.oracle.oracledb.makedsn",
        lambda host, port, service_name: f"{host}:{port}/{service_name}",
    )
    monkeypatch.setattr(
        "oracle_table_compare.oracle.oracledb.connect", lambda **kwargs: kwargs
    )
    connected = connection_from_airflow("oracle_prod")
    assert connected == {
        "user": "reader",
        "password": "secret",
        "dsn": "oracle.example:1521/FREEPDB1",
    }
