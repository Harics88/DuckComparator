import { describe, expect, it } from "vitest";

import {
  cloneRegistry,
  countPreservedFields,
  DEFAULT_REGISTRY,
  listFromText,
  parseRegistry,
  renameComparison,
  serializeRegistry,
  validateRegistry,
} from "../src/registry.js";

describe("registry parsing and serialization", () => {
  it("round-trips unknown fields instead of dropping them", () => {
    const source = `
registry_version: 2
comparisons:
  customer_master:
    description: Customer reconciliation
    owner: data-quality
    left:
      connection: oracle_prod
      schema: CRM
      table: CUSTOMER
      fetch_hint: parallel
    right:
      connection: oracle_uat
      schema: CRM
      table: CUSTOMER
`;
    const document = parseRegistry(source);
    document.comparisons.customer_master.description = "Updated";
    const reparsed = parseRegistry(serializeRegistry(document));
    expect(reparsed.registry_version).toBe(2);
    expect(reparsed.comparisons.customer_master.owner).toBe("data-quality");
    expect(reparsed.comparisons.customer_master.left.fetch_hint).toBe("parallel");
    expect(countPreservedFields(document, "customer_master")).toBe(3);
  });

  it("rejects a scalar YAML document", () => {
    expect(() => parseRegistry("hello")).toThrow("top level");
  });
});

describe("registry validation", () => {
  it("accepts the project example shape", () => {
    expect(validateRegistry(cloneRegistry(DEFAULT_REGISTRY))).toEqual([]);
  });

  it("allows an omitted primary key for Oracle metadata discovery", () => {
    const document = cloneRegistry(DEFAULT_REGISTRY);
    delete document.comparisons.customer_master.primary_key;
    expect(validateRegistry(document)).toEqual([]);
  });

  it("reports missing source identifiers and invalid limits", () => {
    const document = cloneRegistry(DEFAULT_REGISTRY);
    document.comparisons.customer_master.left.connection = "";
    document.comparisons.customer_master.report.detail_row_limit = 0;
    const errors = validateRegistry(document);
    expect(errors.map((error) => error.path)).toContain(
      "comparisons.customer_master.left.connection",
    );
    expect(errors.map((error) => error.path)).toContain(
      "comparisons.customer_master.report.detail_row_limit",
    );
  });
});

describe("editor helpers", () => {
  it("renames a comparison without changing its value", () => {
    const document = cloneRegistry(DEFAULT_REGISTRY);
    const original = document.comparisons.customer_master;
    const name = renameComparison(document, "customer_master", "customer_snapshot");
    expect(name).toBe("customer_snapshot");
    expect(document.comparisons.customer_snapshot).toBe(original);
    expect(document.comparisons.customer_master).toBeUndefined();
  });

  it("prevents invalid and duplicate names", () => {
    const document = cloneRegistry(DEFAULT_REGISTRY);
    document.comparisons.orders = {};
    expect(() => renameComparison(document, "customer_master", "bad name")).toThrow();
    expect(() => renameComparison(document, "customer_master", "orders")).toThrow();
  });

  it("turns comma-separated fields into clean lists", () => {
    expect(listFromText("CUSTOMER_ID, REGION_ID, CUSTOMER_ID ")).toEqual([
      "CUSTOMER_ID",
      "REGION_ID",
      "CUSTOMER_ID",
    ]);
  });
});
