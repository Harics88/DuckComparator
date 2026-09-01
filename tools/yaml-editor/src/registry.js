import yaml from "js-yaml";

export const NAME_PATTERN = /^[A-Za-z0-9_.-]+$/;

export const DEFAULT_REGISTRY = {
  comparisons: {
    customer_master: {
      description: "Customer master reconciliation",
      left: {
        connection: "oracle_prod",
        schema: "CRM",
        table: "CUSTOMER",
      },
      right: {
        connection: "oracle_uat",
        schema: "CRM",
        table: "CUSTOMER",
      },
      primary_key: ["CUSTOMER_ID"],
      exclude_columns: ["LAST_UPDATED_AT"],
      rules: {
        trim_strings: true,
        case_sensitive: false,
        numeric_tolerance: 0.0001,
      },
      report: {
        detail_row_limit: 500000,
      },
    },
  },
};

const isRecord = (value) => value !== null && typeof value === "object" && !Array.isArray(value);

export function cloneRegistry(value) {
  return typeof structuredClone === "function"
    ? structuredClone(value)
    : JSON.parse(JSON.stringify(value));
}

export function parseRegistry(source) {
  const value = yaml.load(source);
  if (value == null) return { comparisons: {} };
  if (!isRecord(value)) {
    throw new Error("The YAML document must contain a mapping at its top level.");
  }
  return value;
}

export function serializeRegistry(document) {
  return yaml.dump(document, {
    noRefs: true,
    lineWidth: 100,
    noCompatMode: true,
    sortKeys: false,
  });
}

export function createComparison() {
  return {
    description: "",
    left: { connection: "", schema: "", table: "" },
    right: { connection: "", schema: "", table: "" },
    primary_key: [],
    exclude_columns: [],
    rules: {
      trim_strings: true,
      case_sensitive: true,
    },
    report: {
      detail_row_limit: 500000,
    },
  };
}

export function nextComparisonName(comparisons) {
  let index = 1;
  let name = "new_comparison";
  while (Object.hasOwn(comparisons, name)) {
    index += 1;
    name = `new_comparison_${index}`;
  }
  return name;
}

export function renameComparison(document, previousName, nextName) {
  const name = nextName.trim();
  if (!NAME_PATTERN.test(name)) {
    throw new Error("Use only letters, numbers, dots, dashes, and underscores.");
  }
  if (name !== previousName && Object.hasOwn(document.comparisons, name)) {
    throw new Error(`A comparison named “${name}” already exists.`);
  }
  if (name === previousName) return name;

  const renamed = {};
  for (const [key, value] of Object.entries(document.comparisons)) {
    renamed[key === previousName ? name : key] = value;
  }
  document.comparisons = renamed;
  return name;
}

export function listFromText(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function validateRegistry(document) {
  const errors = [];
  const add = (path, message) => errors.push({ path, message });

  if (!isRecord(document)) {
    add("document", "The document must be a YAML mapping.");
    return errors;
  }
  if (!isRecord(document.comparisons)) {
    add("comparisons", "Add a top-level comparisons mapping.");
    return errors;
  }

  const entries = Object.entries(document.comparisons);
  if (!entries.length) add("comparisons", "Add at least one comparison before downloading.");

  for (const [name, comparison] of entries) {
    const root = `comparisons.${name}`;
    if (!NAME_PATTERN.test(name)) {
      add(root, "Comparison names may contain only letters, numbers, dots, dashes, and underscores.");
    }
    if (!isRecord(comparison)) {
      add(root, "This comparison must be a mapping.");
      continue;
    }
    if (comparison.description != null && typeof comparison.description !== "string") {
      add(`${root}.description`, "Description must be text.");
    }

    for (const side of ["left", "right"]) {
      const source = comparison[side];
      if (!isRecord(source)) {
        add(`${root}.${side}`, `Add a ${side} source mapping.`);
        continue;
      }
      for (const field of ["connection", "schema", "table"]) {
        if (typeof source[field] !== "string" || !source[field].trim()) {
          add(`${root}.${side}.${field}`, `Enter the ${side} source ${field.replace("connection", "Connection ID")}.`);
        }
      }
    }

    for (const field of ["primary_key", "exclude_columns"]) {
      if (comparison[field] != null) {
        if (!Array.isArray(comparison[field])) {
          add(`${root}.${field}`, `${field.replace("_", " ")} must be a YAML list.`);
        } else if (comparison[field].some((item) => typeof item !== "string" || !item.trim())) {
          add(`${root}.${field}`, `${field.replace("_", " ")} entries must be non-empty text.`);
        }
      }
    }

    if (comparison.rules != null) {
      if (!isRecord(comparison.rules)) {
        add(`${root}.rules`, "Rules must be a mapping.");
      } else {
        for (const field of ["trim_strings", "case_sensitive"]) {
          if (comparison.rules[field] != null && typeof comparison.rules[field] !== "boolean") {
            add(`${root}.rules.${field}`, `${field.replace("_", " ")} must be true or false.`);
          }
        }
        const tolerance = comparison.rules.numeric_tolerance;
        if (
          tolerance != null &&
          (typeof tolerance !== "number" || !Number.isFinite(tolerance) || tolerance < 0)
        ) {
          add(
            `${root}.rules.numeric_tolerance`,
            "Numeric tolerance must be zero or a positive number.",
          );
        }
      }
    }

    if (comparison.report != null) {
      if (!isRecord(comparison.report)) {
        add(`${root}.report`, "Report settings must be a mapping.");
      } else {
        const limit = comparison.report.detail_row_limit;
        if (limit != null && (!Number.isInteger(limit) || limit < 1)) {
          add(`${root}.report.detail_row_limit`, "Detail row limit must be a positive whole number.");
        }
      }
    }
  }
  return errors;
}

const knownComparisonKeys = new Set([
  "description",
  "left",
  "right",
  "primary_key",
  "exclude_columns",
  "rules",
  "report",
]);
const knownSourceKeys = new Set(["connection", "schema", "table"]);
const knownRuleKeys = new Set(["trim_strings", "case_sensitive", "numeric_tolerance"]);
const knownReportKeys = new Set(["detail_row_limit"]);

export function countPreservedFields(document, comparisonName) {
  let count = Object.keys(document).filter((key) => key !== "comparisons").length;
  const comparison = document.comparisons?.[comparisonName];
  if (!isRecord(comparison)) return count;
  count += Object.keys(comparison).filter((key) => !knownComparisonKeys.has(key)).length;
  for (const side of ["left", "right"]) {
    if (isRecord(comparison[side])) {
      count += Object.keys(comparison[side]).filter((key) => !knownSourceKeys.has(key)).length;
    }
  }
  if (isRecord(comparison.rules)) {
    count += Object.keys(comparison.rules).filter((key) => !knownRuleKeys.has(key)).length;
  }
  if (isRecord(comparison.report)) {
    count += Object.keys(comparison.report).filter((key) => !knownReportKeys.has(key)).length;
  }
  return count;
}
