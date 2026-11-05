# Local data quickstart

From this source checkout, create an isolated Python3.11+ environment and install the local profile. No package has been published to PyPI.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install '.[pandas]'
.venv/bin/python -m gmldf validate --config examples/data-only/workflow.yaml
.venv/bin/python -m gmldf run --config examples/data-only/workflow.yaml --profile local --run-id data_demo --output-dir runs
```

Offline validation checks configuration only. The run reads the three synthetic records in `examples/data-only/input.csv`, selects two columns, casts amount to float64 and sorts by record ID. The fixture is hand-authored with IDs a/b/c, amounts1.25/2.5/null and arbitrary categories; it contains no copied or customer data.

Relative paths resolve against the config directory. The local run creates its metadata directory and the example's output parent. Expected `examples/data-only/runs/result.csv`:

```csv
record_id,amount
a,1.25
b,2.5
c,NULL
```

The exact run result appears on stdout and in `examples/data-only/runs/data_demo/result.json`; progress goes to stderr. `identity.json` records the runtime versions/config digest. Every output is mandatory and independently committed. Existing run IDs and existing CSV outputs are protected; a new invocation needs a new run ID and a fresh configured destination (or explicit output overwrite mode). Do not delete or overwrite completed business outputs just to rerun a demo.

Change source/output locations and supported operation parameters in YAML; no library source edits are required. Preserve explicit framing/null settings and quote the YAML string `'NULL'`. Parent directories for other configured destinations must already exist. An invalid configuration or unsupported capability rejects before business reads/writes.

Verified profile: CPython3.11.18/macOS arm64 with the pinned pandas extra. Other engines/connectors, model training/inference, cancellation/recovery and external hosts remain backlog work. This synthetic example does not reduce the generic first-release scope. See [compatibility evidence](compatibility.md) and [local execution semantics](local-execution.md).
