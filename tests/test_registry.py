from oracle_table_compare.registry import load_comparison


def test_loads_example_registry() -> None:
    comparison = load_comparison("configs/comparisons.example.yaml", "customer_master")
    assert comparison.primary_key == ("CUSTOMER_ID",)
    assert comparison.left.connection == "oracle_prod"


def test_registry_allows_oracle_key_discovery(tmp_path) -> None:
    path = tmp_path / "comparisons.yaml"
    path.write_text(
        "comparisons:\n  auto:\n    left: {connection: left, schema: CRM, table: CUSTOMER}\n"
        "    right: {connection: right, schema: CRM, table: CUSTOMER}\n",
        encoding="utf-8",
    )
    assert load_comparison(path, "auto").primary_key == ()


def test_registry_rejects_unsafe_comparison_name() -> None:
    try:
        load_comparison("configs/comparisons.example.yaml", "../customer_master")
    except ValueError as error:
        assert "Comparison names" in str(error)
    else:
        raise AssertionError("unsafe comparison name was accepted")
