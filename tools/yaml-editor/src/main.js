import "./styles.css";

import {
  cloneRegistry,
  countPreservedFields,
  createComparison,
  DEFAULT_REGISTRY,
  listFromText,
  nextComparisonName,
  parseRegistry,
  renameComparison,
  serializeRegistry,
  validateRegistry,
} from "./registry.js";

const app = document.querySelector("#app");

const state = {
  document: cloneRegistry(DEFAULT_REGISTRY),
  selected: "customer_master",
  filename: "comparisons.example.yaml",
  filter: "",
  loadError: "",
  notice: "Loaded the project example. Open a YAML file or begin editing.",
};

const icons = {
  open: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 6.5h6l2 2h9v10a2 2 0 0 1-2 2h-15z"/><path d="M3.5 8.5v-3a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v1"/></svg>',
  download: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12m-4-4 4 4 4-4"/><path d="M4 17v3h16v-3"/></svg>',
  plus: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  trash: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7"/><path d="M10 11v5m4-5v5"/></svg>',
  search: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/></svg>',
  check: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>',
  warning: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2.5 20h19z"/><path d="M12 9v4m0 3.5v.5"/></svg>',
  shield: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 5 6v5c0 4.7 2.8 8 7 10 4.2-2 7-5.3 7-10V6z"/><path d="m9 12 2 2 4-5"/></svg>',
  file: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5"/></svg>',
};

const esc = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const selectedComparison = () => state.document.comparisons?.[state.selected];

function getValue(path, fallback = "") {
  let value = selectedComparison();
  for (const key of path.split(".")) value = value?.[key];
  return value ?? fallback;
}

function setValue(path, value, { removeWhenEmpty = false } = {}) {
  const keys = path.split(".");
  let target = selectedComparison();
  if (!target) return;
  for (const key of keys.slice(0, -1)) {
    if (!target[key] || typeof target[key] !== "object" || Array.isArray(target[key])) {
      target[key] = {};
    }
    target = target[key];
  }
  const finalKey = keys.at(-1);
  if (removeWhenEmpty && value === "") delete target[finalKey];
  else target[finalKey] = value;
}

function errorsForSelected() {
  const prefix = `comparisons.${state.selected}`;
  return validateRegistry(state.document).filter(
    (error) => error.path === prefix || error.path.startsWith(`${prefix}.`),
  );
}

function fieldError(path) {
  const fullPath = `comparisons.${state.selected}.${path}`;
  return validateRegistry(state.document).find((error) => error.path === fullPath);
}

function field({ label, path, value, type = "text", help = "", required = false, input = "input", min, step }) {
  const error = fieldError(path);
  const id = `field-${path.replaceAll(".", "-")}`;
  const describedBy = [help ? `${id}-help` : "", error ? `${id}-error` : ""].filter(Boolean).join(" ");
  const attrs = [
    `id="${id}"`,
    `data-field="${esc(path)}"`,
    `aria-invalid="${error ? "true" : "false"}"`,
    describedBy ? `aria-describedby="${describedBy}"` : "",
    required ? "required" : "",
    min != null ? `min="${min}"` : "",
    step != null ? `step="${step}"` : "",
  ].filter(Boolean).join(" ");
  const control = input === "textarea"
    ? `<textarea ${attrs}>${esc(value)}</textarea>`
    : `<input ${attrs} type="${type}" value="${esc(value)}">`;
  return `
    <div class="field ${error ? "field-invalid" : ""}">
      <label for="${id}">${esc(label)}${required ? '<span aria-hidden="true"> *</span>' : ""}</label>
      ${control}
      ${help ? `<span class="field-help" id="${id}-help">${esc(help)}</span>` : ""}
      ${error ? `<span class="field-error" id="${id}-error">${icons.warning}${esc(error.message)}</span>` : ""}
    </div>`;
}

function checkbox(label, path, checked, help) {
  const id = `field-${path.replaceAll(".", "-")}`;
  return `
    <label class="check-field" for="${id}">
      <input id="${id}" type="checkbox" data-boolean-field="${esc(path)}" ${checked ? "checked" : ""}>
      <span class="check-control" aria-hidden="true">${icons.check}</span>
      <span><strong>${esc(label)}</strong><small>${esc(help)}</small></span>
    </label>`;
}

function validationMarkup(errors) {
  if (!errors.length) {
    return `<div class="validation-state is-valid" role="status">${icons.check}<span><strong>Registry valid</strong><small>No errors found.</small></span></div>`;
  }
  return `<div class="validation-state is-review" role="status">${icons.warning}<span><strong>${errors.length} ${errors.length === 1 ? "issue" : "issues"} to review</strong><small>Fix validation errors before downloading.</small></span></div>`;
}

function comparisonList(errors) {
  const names = Object.keys(state.document.comparisons ?? {});
  const query = state.filter.trim().toLocaleLowerCase();
  const filtered = names.filter((name) => name.toLocaleLowerCase().includes(query));
  if (!filtered.length) {
    return `<div class="empty-list"><strong>No comparisons found</strong><span>${query ? "Try a different search." : "Add a comparison to start the registry."}</span></div>`;
  }
  return filtered.map((name) => {
    const comparison = state.document.comparisons[name];
    const itemErrors = errors.filter(
      (error) => error.path === `comparisons.${name}` || error.path.startsWith(`comparisons.${name}.`),
    );
    const left = comparison?.left;
    const right = comparison?.right;
    const sourceLine = left?.connection || right?.connection
      ? `${left?.connection || "Left unset"} ↔ ${right?.connection || "Right unset"}`
      : "Sources not configured";
    return `
      <button class="comparison-item ${name === state.selected ? "is-selected" : ""}" data-select="${esc(name)}" type="button" aria-current="${name === state.selected ? "true" : "false"}">
        <span class="item-state ${itemErrors.length ? "is-review" : "is-valid"}" aria-hidden="true"></span>
        <span class="item-copy"><strong>${esc(name)}</strong><small>${esc(sourceLine)}</small></span>
        <span class="item-count">${itemErrors.length ? itemErrors.length : "✓"}<span class="sr-only">${itemErrors.length ? " validation issues" : " valid"}</span></span>
      </button>`;
  }).join("");
}

function editorMarkup() {
  const comparison = selectedComparison();
  if (!comparison) {
    return `
      <section class="empty-workspace" aria-labelledby="empty-title">
        <div class="empty-symbol">${icons.file}</div>
        <h1 id="empty-title">Start your comparison registry</h1>
        <p>Add a comparison or open an existing YAML file. Credentials remain in Airflow Connections—not in this editor.</p>
        <button class="button button-primary" id="empty-add" type="button">${icons.plus} Add comparison</button>
      </section>`;
  }

  const preserved = countPreservedFields(state.document, state.selected);
  const selectedErrors = errorsForSelected();
  return `
    <section class="editor" aria-labelledby="editor-heading">
      <div class="editor-heading-row">
        <div>
          <span class="section-context">Editing comparison</span>
          <h1 id="editor-heading">${esc(state.selected)}</h1>
        </div>
        <div class="editor-heading-actions">
          ${preserved ? `<span class="preserved-note" title="Unknown fields remain in the YAML output">${icons.shield} Preserving ${preserved} additional ${preserved === 1 ? "field" : "fields"}</span>` : ""}
          <button class="icon-button danger-button" id="delete-comparison" type="button" aria-label="Delete ${esc(state.selected)}">${icons.trash}</button>
        </div>
      </div>

      ${selectedErrors.length ? `
        <section class="error-summary" aria-labelledby="error-summary-title" role="alert">
          ${icons.warning}<div><strong id="error-summary-title">Review this comparison</strong>
          <ul>${selectedErrors.slice(0, 4).map((error) => `<li>${esc(error.message)}</li>`).join("")}</ul>
          ${selectedErrors.length > 4 ? `<small>And ${selectedErrors.length - 4} more ${selectedErrors.length - 4 === 1 ? "issue" : "issues"} below.</small>` : ""}</div>
        </section>` : ""}

      <form id="comparison-form" novalidate>
        <section class="ledger-section identity-section" aria-labelledby="identity-heading">
          <div class="section-heading"><span>1</span><div><h2 id="identity-heading">Identity</h2><p>Name this reusable comparison.</p></div></div>
          <div class="field-grid two-columns">
            ${field({ label: "Comparison name", path: "$name", value: state.selected, required: true, help: "Letters, numbers, dots, dashes, and underscores." })}
            ${field({ label: "Description", path: "description", value: comparison.description ?? "", help: "Shown in generated comparison reports." })}
          </div>
        </section>

        <section class="ledger-section" aria-labelledby="sources-heading">
          <div class="section-heading"><span>2</span><div><h2 id="sources-heading">Sources</h2><p>Reference Airflow Connection IDs only. Never enter Oracle credentials.</p></div></div>
          <div class="source-grid">
            <fieldset>
              <legend><span>Left</span> Baseline source</legend>
              ${field({ label: "Airflow Connection ID", path: "left.connection", value: getValue("left.connection"), required: true, help: "Example: oracle_prod" })}
              <div class="field-grid two-columns">
                ${field({ label: "Schema", path: "left.schema", value: getValue("left.schema"), required: true })}
                ${field({ label: "Table or view", path: "left.table", value: getValue("left.table"), required: true })}
              </div>
            </fieldset>
            <div class="source-divider" aria-hidden="true">↔</div>
            <fieldset>
              <legend><span>Right</span> Comparison source</legend>
              ${field({ label: "Airflow Connection ID", path: "right.connection", value: getValue("right.connection"), required: true, help: "Example: oracle_uat" })}
              <div class="field-grid two-columns">
                ${field({ label: "Schema", path: "right.schema", value: getValue("right.schema"), required: true })}
                ${field({ label: "Table or view", path: "right.table", value: getValue("right.table"), required: true })}
              </div>
            </fieldset>
          </div>
        </section>

        <section class="ledger-section" aria-labelledby="keys-heading">
          <div class="section-heading"><span>3</span><div><h2 id="keys-heading">Keys and exclusions</h2><p>Use comma-separated Oracle column names.</p></div></div>
          <div class="field-grid two-columns">
            ${field({ label: "Primary-key columns", path: "primary_key", value: (comparison.primary_key ?? []).join(", "), help: "Optional. Leave blank to discover declared Oracle primary keys." })}
            ${field({ label: "Excluded columns", path: "exclude_columns", value: (comparison.exclude_columns ?? []).join(", "), help: "Columns ignored during value comparison." })}
          </div>
        </section>

        <section class="ledger-section" aria-labelledby="rules-heading">
          <div class="section-heading"><span>4</span><div><h2 id="rules-heading">Normalization and tolerance</h2><p>Make comparison behavior explicit and repeatable.</p></div></div>
          <div class="rules-layout">
            <div class="check-group">
              ${checkbox("Trim strings", "rules.trim_strings", getValue("rules.trim_strings", true), "Ignore leading and trailing whitespace.")}
              ${checkbox("Case-sensitive strings", "rules.case_sensitive", getValue("rules.case_sensitive", true), "Treat uppercase and lowercase values as different.")}
            </div>
            ${field({ label: "Numeric tolerance", path: "rules.numeric_tolerance", value: getValue("rules.numeric_tolerance"), type: "number", min: 0, step: "any", help: "Optional absolute difference treated as equal." })}
          </div>
        </section>

        <section class="ledger-section report-section" aria-labelledby="report-heading">
          <div class="section-heading"><span>5</span><div><h2 id="report-heading">Report output</h2><p>Keep detailed Excel evidence usable at scale.</p></div></div>
          <div class="compact-field">
            ${field({ label: "Detail row limit", path: "report.detail_row_limit", value: getValue("report.detail_row_limit", 500000), type: "number", min: 1, step: 1, required: true, help: "Maximum rows written to each evidence sheet." })}
          </div>
        </section>
      </form>

      <details class="preview-panel" open>
        <summary><span>${icons.file}<strong>YAML preview</strong><small>Read-only · full registry</small></span><span class="summary-action">Show or hide</span></summary>
        <pre tabindex="0" aria-label="Generated YAML preview"><code id="yaml-preview">${esc(serializeRegistry(state.document))}</code></pre>
      </details>
    </section>`;
}

function render({ focusName = false } = {}) {
  if (!state.document.comparisons || typeof state.document.comparisons !== "object" || Array.isArray(state.document.comparisons)) {
    state.document.comparisons = {};
  }
  if (!Object.hasOwn(state.document.comparisons, state.selected)) {
    state.selected = Object.keys(state.document.comparisons)[0] ?? "";
  }
  const errors = validateRegistry(state.document);
  app.innerHTML = `
    <a class="skip-link" href="#workspace">Skip to editor</a>
    <header class="app-header">
      <div class="brand"><span class="brand-mark" aria-hidden="true">DC</span><span><strong>DuckComparator</strong><small>YAML Registry Editor</small></span></div>
      <div class="file-context">${icons.file}<span><strong>${esc(state.filename)}</strong><small>Local browser session</small></span></div>
      <div class="header-actions">
        <input id="file-input" class="sr-only" type="file" accept=".yaml,.yml,text/yaml,application/yaml">
        <button class="button button-secondary" id="open-file" type="button">${icons.open}<span>Open YAML</span></button>
        ${validationMarkup(errors)}
        <button class="button button-primary" id="download-file" type="button" ${errors.length ? "disabled" : ""}>${icons.download}<span>Download YAML</span></button>
      </div>
    </header>
    ${state.loadError ? `<div class="load-error" role="alert">${icons.warning}<span><strong>We couldn’t open that YAML file.</strong>${esc(state.loadError)} Fix the file and try again.</span><button type="button" id="dismiss-error" aria-label="Dismiss file error">×</button></div>` : ""}
    <div class="notice-bar" role="status" aria-live="polite"><span>${icons.shield}${esc(state.notice)}</span><strong>No credentials are read or stored.</strong></div>
    <div class="workspace" id="workspace">
      <aside class="comparison-rail" aria-labelledby="comparisons-heading">
        <div class="rail-heading"><div><h2 id="comparisons-heading">Comparisons</h2><span>${Object.keys(state.document.comparisons).length}</span></div><button class="button button-secondary button-block" id="add-comparison" type="button">${icons.plus} Add comparison</button></div>
        <label class="search-field" for="comparison-search">${icons.search}<span class="sr-only">Search comparisons</span><input id="comparison-search" type="search" placeholder="Search comparisons" value="${esc(state.filter)}"></label>
        <nav class="comparison-list" aria-label="Registry comparisons">${comparisonList(errors)}</nav>
      </aside>
      <main>${editorMarkup()}</main>
    </div>`;
  bindEvents();
  if (focusName) document.querySelector('[data-field="$name"]')?.focus();
}

function refreshDerivedState() {
  const errors = validateRegistry(state.document);
  const headerState = document.querySelector(".validation-state");
  if (headerState) headerState.outerHTML = validationMarkup(errors);
  const download = document.querySelector("#download-file");
  if (download) download.disabled = errors.length > 0;
  const preview = document.querySelector("#yaml-preview");
  if (preview) preview.textContent = serializeRegistry(state.document);
  document.querySelectorAll("[data-field]").forEach((control) => {
    if (control.dataset.field === "$name") return;
    const error = fieldError(control.dataset.field);
    const wrapper = control.closest(".field");
    const errorId = `${control.id}-error`;
    const existingError = wrapper?.querySelector(".field-error");
    control.setAttribute("aria-invalid", error ? "true" : "false");
    wrapper?.classList.toggle("field-invalid", Boolean(error));
    const describedBy = new Set((control.getAttribute("aria-describedby") ?? "").split(" ").filter(Boolean));
    if (error) {
      describedBy.add(errorId);
      const message = `<span class="field-error" id="${errorId}">${icons.warning}${esc(error.message)}</span>`;
      if (existingError) existingError.outerHTML = message;
      else wrapper?.insertAdjacentHTML("beforeend", message);
    } else {
      describedBy.delete(errorId);
      existingError?.remove();
    }
    if (describedBy.size) control.setAttribute("aria-describedby", [...describedBy].join(" "));
    else control.removeAttribute("aria-describedby");
  });
  const notice = document.querySelector(".notice-bar span");
  if (notice) notice.innerHTML = `${icons.shield}${errors.length ? `${errors.length} ${errors.length === 1 ? "issue needs" : "issues need"} attention before download.` : "Changes are ready to download."}`;
}

function addComparison() {
  const comparisons = state.document.comparisons;
  const name = nextComparisonName(comparisons);
  comparisons[name] = createComparison();
  state.selected = name;
  state.notice = "Comparison added. Complete the required source fields.";
  render({ focusName: true });
}

function bindEvents() {
  document.querySelector("#open-file")?.addEventListener("click", () => {
    document.querySelector("#file-input").click();
  });

  document.querySelector("#file-input")?.addEventListener("change", async (event) => {
    const [file] = event.target.files;
    if (!file) return;
    try {
      const document = parseRegistry(await file.text());
      state.document = document;
      state.filename = file.name;
      state.selected = Object.keys(document.comparisons ?? {})[0] ?? "";
      state.loadError = "";
      state.notice = `Opened ${file.name}. Unknown fields will be preserved when downloaded.`;
      render();
    } catch (error) {
      state.loadError = error instanceof Error ? error.message : String(error);
      render();
    }
  });

  document.querySelector("#dismiss-error")?.addEventListener("click", () => {
    state.loadError = "";
    render();
  });

  document.querySelector("#download-file")?.addEventListener("click", () => {
    const errors = validateRegistry(state.document);
    if (errors.length) {
      state.notice = "Fix validation errors before downloading.";
      render();
      return;
    }
    const blob = new Blob([serializeRegistry(state.document)], { type: "application/yaml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = state.filename.match(/\.ya?ml$/i) ? state.filename : "comparisons.yaml";
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    state.notice = `Downloaded ${anchor.download}.`;
    refreshDerivedState();
  });

  document.querySelector("#add-comparison")?.addEventListener("click", addComparison);
  document.querySelector("#empty-add")?.addEventListener("click", addComparison);

  document.querySelector("#comparison-search")?.addEventListener("input", (event) => {
    state.filter = event.target.value;
    const errors = validateRegistry(state.document);
    document.querySelector(".comparison-list").innerHTML = comparisonList(errors);
    bindComparisonSelection();
  });
  bindComparisonSelection();

  document.querySelector("#delete-comparison")?.addEventListener("click", () => {
    const name = state.selected;
    if (!window.confirm(`Delete “${name}” from this local registry draft?`)) return;
    delete state.document.comparisons[name];
    state.selected = Object.keys(state.document.comparisons)[0] ?? "";
    state.notice = `Deleted ${name} from the local draft.`;
    render();
  });

  document.querySelectorAll("[data-field]").forEach((control) => {
    const path = control.dataset.field;
    const eventName = path === "$name" ? "change" : "input";
    control.addEventListener(eventName, (event) => {
      let value = event.target.value;
      if (path === "$name") {
        try {
          state.selected = renameComparison(state.document, state.selected, value);
          state.notice = `Renamed comparison to ${state.selected}.`;
          render();
        } catch (error) {
          event.target.setCustomValidity(error.message);
          event.target.reportValidity();
        }
        return;
      }
      if (path === "primary_key" || path === "exclude_columns") {
        value = listFromText(value);
        if (!value.length) {
          delete selectedComparison()[path];
        } else {
          setValue(path, value);
        }
      } else if (path === "rules.numeric_tolerance") {
        setValue(path, value === "" ? "" : Number(value), { removeWhenEmpty: true });
      } else if (path === "report.detail_row_limit") {
        setValue(path, value === "" ? "" : Number(value), { removeWhenEmpty: true });
      } else {
        setValue(path, value);
      }
      refreshDerivedState();
    });
  });

  document.querySelectorAll("[data-boolean-field]").forEach((control) => {
    control.addEventListener("change", (event) => {
      setValue(event.target.dataset.booleanField, event.target.checked);
      refreshDerivedState();
    });
  });
}

function bindComparisonSelection() {
  document.querySelectorAll("[data-select]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selected = button.dataset.select;
      state.notice = `Editing ${state.selected}.`;
      render();
    });
  });
}

render();
