# Local CLI execution

Install the local optional profile (`python -m pip install '.[pandas]'` from this checkout), then invoke:

```sh
python -m gmldf run --config /path/to/workflow.yaml --profile local --run-id data_demo --output-dir runs
```

This currently executes data-only pandas CSV workflows with select/cast/sort. Unsupported engines, host profiles, connectors and workflow kinds reject before business data access. Engine selection comes only from config. The command uses the same workflow runner as Python coordination; `gmldf.execution.local.run_local(config_path, profile=..., run_id=..., output_dir=Path(...))` returns its `RunResult`.

Relative source/output locations, relative local `file:` URIs and relative `--output-dir` resolve against the config directory. Absolute paths remain absolute. The output directory holds a per-run subdirectory, so this command reserves `<config directory>/runs/data_demo/`. It writes `identity.json` and `result.json` there using atomic no-replacement publication. Configured business outputs may not alias those reserved paths.

Run IDs use letters, digits, underscores and hyphens, starting with a letter. Any existing per-run directory/file, including a partial failed invocation, rejects reuse. Run-ID uniqueness is scoped to the selected output directory; there is no global registry. Choose a new ID for another invocation. No automatic retry/resume occurs, and this guard does not turn multiple business outputs into a transaction.

The identity contains an attempt ID, digest of the redacted resolved config, package version, Python/platform and selected provider dependency versions. Raw config/data and credentials are not written into metadata. A successful or failed workflow result is persisted and printed as JSON on stdout; coarse started/terminal progress events go to stderr. Preflight or metadata-publication failure emits a safe error to stderr. Failed metadata publication can occur after business outputs committed; never retry blindly.

Exit codes: 0 success; 2 config/capability/policy rejection; 1 execution/output failure; 130 for a confirmed cancelled result. Worker cancellation/deadline enforcement is pending T031. An interrupt does not currently certify stopped backend work or yield a confirmed cancelled result. Progress at individual stages and durable recovery remain later tasks.
