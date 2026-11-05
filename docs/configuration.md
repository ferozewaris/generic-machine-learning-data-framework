# Configuration schema version 1

Implemented now: offline structure, bounded safe YAML, and reference validation through Python or CLI. Data reads, processing, model training, artifact persistence, and backend capability checks are subsequent tasks. A successful validation report has `capabilities_checked: false`.

```sh
.venv/bin/python -m gmldf validate --config examples/validation/workflow.yaml
.venv/bin/python -m gmldf validate --config examples/validation/workflow.yaml --output validation.json
```

Only the requested report is written. Existing report files, including the source config itself, are never overwritten. The report contains workflow identity and validation scope, not connection options or credentials.

Python callers can use `gmldf.core.config.load_config(path)` or `validate_config(mapping)`. Both return a typed `WorkflowSpec` or raise `ConfigError` with `code`, `path`, and `reason`. This does not yet provide the later public workflow-execution API.

## Required root fields

| Field | Meaning |
|---|---|
| `schema_version` | Integer `1`; booleans and strings do not count |
| `name` | Nonempty descriptive workflow label |
| `kind` | `data`, `train`, or `infer` |
| `engine` | Explicit `spark`, `pandas`, `polars`, or `duckdb` |
| `execution` | Current host's `profile`; optional positive `timeout_seconds` and `memory_bytes` |
| `sources` | Nonempty list of named source specifications |
| `steps` | List of transformation steps; may be empty |
| `outputs` | Nonempty list of output destinations |

Optional `connections` maps connection ids to `options` and `credential_refs`. Reference values name secrets; validation does not resolve them. Unknown fields at declared schema boundaries are rejected. Provider-specific `options`, step `params`, algorithm parameters/search spaces, and split details are finite JSON values; their backend-specific meaning is not validated until the relevant provider exists.

## Sources, steps, and outputs

- Sources: `id`, `connector`, exactly one of `location`/`table`/`query`; optional named `connection`, `format`, `columns`, and `options`.
- Steps: `id`, `operation`, nonempty `inputs` list, optional `params`. Source/step ids share one unique namespace. Forward references are valid if the graph is acyclic.
- Outputs: `id`, `dataset`, `connector`, exactly one of `location`/`table`; optional `connection`, `format`, `mode`, and `options`.
- Output mode defaults to `error_if_exists`; other representable modes are `append`, `overwrite`, and `upsert`. Offline representation does not establish provider support for a mode.
- Connector ids are `csv`, `parquet`, `s3`, `sqlserver`, `oracle`, `databricks`, `snowflake`, `adls`, `gcs`, and `delta`. Formats are `csv`, `parquet`, and `delta`.
- Output datasets reference named source/step ids. Training may additionally reference `ml.test_predictions`; inference may reference `ml.predictions`.
- Ids start with a letter and contain letters, digits, underscores, or hyphens, up to 128 characters. Column names and human labels are not restricted to that identifier grammar.

No configured file, database, connector, secret store, or network endpoint is contacted during offline validation. The validation example intentionally names a nonexistent input file.

## Training and inference

Training requires `ml` and forbids `model`; inference requires `model: {uri: "immutable-artifact-reference"}` and forbids `ml`. Data-only workflows forbid both.

```yaml
ml:
  task: classification
  target: label
  features: [amount, age]
  algorithms:
    - name: sklearn.logistic_regression
      parameters: {}
      search_space:
        C: [0.1, 1.0, 10.0]
  evaluation:
    metric: roc_auc
  tuning:
    max_trials: 8
    timeout_seconds: 300
    seed: 42
  refit_on_all_data: false
```

All four tasks are representable: classification, regression, forecasting, clustering. Task, algorithm list, metric, trial cap, and timeout are explicit. No installed algorithm or baseline is automatically added. An omitted algorithm `search_space` is retained as unspecified for the future versioned-default resolver, not expanded during structural validation.

Optional task fields are `target`, `features`, `time_column`, `group_columns`, `frequency`, positive `horizon`, and `split`. Required task-specific data/algorithm/metric compatibility belongs to later task/provider preflight; arbitrary nonempty algorithm and metric ids are not currently claimed supported.

`refit_on_all_data` defaults to false. Omitted `input_transfer` is disabled; the current explicit transfer object contains `enabled`, `source_engine`, `target_engine`, positive `max_rows`, and positive `max_bytes`. No transfer or refit is performed by validation.

## Input and error limits

- Maximum 1 MiB for the UTF-8 YAML file and normalized JSON-equivalent configuration.
- Maximum nesting depth 50 and 20,000 values/keys; limits apply before YAML object construction and before Pydantic validation of Python mappings.
- Reject duplicate keys, aliases, recursive structures, unsafe YAML tags, non-string keys, non-JSON values, and non-finite numbers.
- PyYAML scalar conventions apply; quote date/time strings to prevent implicit timestamp objects.
- CLI `--profile` is an explicitly requested profile override and is validated with the same schema.
- Exit 0: valid offline config; exit 2: invalid/unreadable config; exit 1: report could not be written. Structured errors go to stderr without rejected values or tracebacks.

See the [implementation decisions](decisions/library-contract.md) and [compatibility evidence](compatibility.md). These limits are defensive input bounds, not dataset-size or model-training limits.
