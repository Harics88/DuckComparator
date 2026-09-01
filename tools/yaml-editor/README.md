# DuckComparator YAML Registry Editor

A local, browser-based editor for DuckComparator comparison registries. It opens YAML from your computer, presents supported registry fields as a guided form, validates the full registry, previews generated YAML, and downloads a new local file.

The editor never asks for Oracle credentials. Source connection fields accept Airflow Connection IDs only.

## Start locally

From `tools/yaml-editor`:

```text
npm install
npm run dev
```

Open the local address shown in the terminal, normally `http://127.0.0.1:5173`.

## Production build

```text
npm run build
npm run preview
```

The static build is written to `tools/yaml-editor/dist`. It has no runtime server, database, login, or external web-resource dependency. Serve that directory through any approved static-file server.

## Run tests

```text
npm test
npm run test:browser
```

The browser smoke test uses an installed Google Chrome browser by default. Set `PLAYWRIGHT_CHROME_PATH` when Chrome is installed at a non-standard location.

## Editor behavior

- Supports multiple named comparisons.
- Edits left and right Connection IDs, schemas, and tables.
- Supports optional composite primary keys and excluded columns.
- Edits string trimming, case sensitivity, numeric tolerance, and report detail limits.
- Disables YAML download until the registry passes validation.
- Preserves unknown mappings and values that are not represented by the form.
- Processes opened files entirely in the browser and downloads the result locally.

YAML comments, anchors, aliases, and original formatting are not preserved because the file is parsed into data and serialized again. Unknown data fields are preserved unless their containing supported field is deliberately replaced through the form.

## Safe workflow

1. Open a registry YAML file.
2. Confirm the filename and comparison count.
3. Edit supported fields in the ledger form.
4. Review validation messages and the complete YAML preview.
5. Download the registry only when the status reads `Registry valid`.
6. Review the downloaded diff before deploying it to Airflow.
