# Task List: Generic Data and Machine Learning Library

Status: Revised to the user-confirmed intent on 2026-11-05. Implementation has started; completed tasks include evidence below.
Intent: [confirmed intent](../docs/intent/generic-data-ml-library.md). Plan: [plan.md](plan.md).

## First-release completion rule

All originally requested connectors, four processing engines, four task families, requested ML integrations, outputs, and compatible host invocation belong to the first release.
Examples and intermediate milestones do not reduce that scope. A verified supported combination is required for each named capability; the full Cartesian product is not promised.
The library runs through Python/CLI in the user's host. It does not provision infrastructure or manage remote jobs.

## How to use this backlog

- 87 stable task ids: 86 required tasks plus optional T080 for a user's business dataset. Task checkmarks reflect recorded decision artifacts or executed acceptance checks; each completed task includes evidence.
- Original ids T001–T084 are retained. Host-control tasks were re-scoped to library installation/context/invocation. T085–T087 explicitly cover optional full-data refit, default tuning domains, and required config intent.
- Tasks are displayed in dependency order. Newly added ids may precede older consumers; numeric id alone is not the execution order.
- Each task has at most three acceptance criteria and five likely files; split a task before implementation if real scope exceeds that or one focused session.
- Commands/files are prospective. Tests establish behavior only after implementation; unavailable live environments remain unresolved evidence, never a mocked or skipped pass.
- Optional T080 can remain unchecked without blocking the generic release. All other required capabilities and their evidence must complete.
- Checkpoints follow each three displayed tasks. Review required work and keep the optional business-data task separate; do not hold unrelated work for a missing optional dataset.
- Existing host/credential/resource authorization governs live checks. Documentation does not authorize package publishing, remote launches, infrastructure changes, or paid/destructive activity.

## Stage 01: T001, T002, T003

<a id="t001"></a>

### [x] T001: Record remaining implementation defaults

**Description:** Carry the confirmed product decisions into engineering defaults without reopening release scope.

**Spec:** [SPEC-core-contracts.md](../SPEC-core-contracts.md)

**Acceptance criteria:**

- [x] Reference the confirmed intent and record package name, Python range, schema library, and input limits as implementation decisions.
- [x] Document that every named connector/engine/task is first-release scope; fixtures, metrics, horizons, and budgets are configurable examples, not product defaults.
- [x] Keep unresolved dependency/host details explicit without blocking independent tasks or silently approving untested support.

**Verification:**

```sh
git diff --check
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Product intent is confirmed. Only unresolved technical choices need resolution before their implementation; routine choices can be proposed with rationale.

**Dependencies:** None

**Files likely touched:**

- `docs/decisions/library-contract.md`
- `SPEC-core-contracts.md`
- `docs/configuration.md`

**Estimated scope:** Medium (3 files).

**Evidence (2026-11-05):** Recorded package/Python/schema/limit choices in docs/decisions/library-contract.md; first-release scope unchanged.


<a id="t002"></a>

### [x] T002: Bound installation and host compatibility

**Description:** Define tested invocation profiles for the user's hosts without selecting an orchestration service.

**Spec:** [SPEC-execution.md](../SPEC-execution.md)

**Acceptance criteria:**

- [x] Define Python/dependency/CPU/driver/session profiles to test locally, inside containers/Kubernetes, AWS-hosted environments, Databricks, and Snowflake.
- [x] Separate platform connectors from execution inside a platform, declaring actual compatible engine/task pairs and unsupported modes.
- [x] Record existing identity/network/storage and test prerequisites; no EKS/ECS/Batch/SageMaker choice or remote-job API is required.

**Verification:**

```sh
git diff --check
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Environment-specific verification requires actual available authorized hosts; no provisioning is included.

**Dependencies:** T001

**Files likely touched:**

- `docs/decisions/host-compatibility.md`
- `docs/compatibility.md`
- `SPEC-execution.md`

**Estimated scope:** Medium (3 files).

**Evidence (2026-11-05):** Recorded all required host profiles and prerequisites in docs/decisions/host-compatibility.md; external live evidence remains planned.


<a id="t003"></a>

### [x] T003: Create an installable minimal package

**Description:** Select and pin the minimal development/core dependencies; do not install all optional backends.

**Spec:** [SPEC-core-contracts.md](../SPEC-core-contracts.md)

**Acceptance criteria:**

- [x] Editable base install and wheel build work with the confirmed Python target.
- [x] Base import requires no pandas, Spark, MLflow, or cloud SDK; optional extras are documented.
- [x] pytest/Ruff/build tooling and pytest integration markers are configured without adding CI or a service.

**Verification:**

```sh
python3 -m pytest tests/unit/test_install.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T001

**Files likely touched:**

- `pyproject.toml`
- `src/gmldf/__init__.py`
- `tests/unit/test_install.py`
- `.gitignore`
- `docs/development.md`

**Estimated scope:** Medium (5 files).

**Evidence (2026-11-05):** RED: installation test failed before the package existed. GREEN: isolated editable install, pytest, Ruff, and source/wheel build passed on CPython 3.11.18 macOS arm64. Tested core: Pydantic 2.14.3 and PyYAML 6.0.3; dev: pytest 9.2.0, Ruff 0.17.3, build 1.6.1, Hatchling 1.33.0.


### Checkpoint C01: After T001, T002, T003

- [x] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [x] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [x] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 02: T004, T005, T006

<a id="t004"></a>

### [x] T004: Validate configuration through the CLI

**Description:** Deliver this core-contracts capability through the provider contracts, keeping previously completed paths working.

Implementation slices (same task id, independent red–green checks): T004a strict models and shape tests; T004b bounded YAML/reference validation; T004c CLI/report contract and documentation. Each slice changes at most five implementation files; task evidence is tracked here separately.

**Spec:** [SPEC-core-contracts.md](../SPEC-core-contracts.md)

**Acceptance criteria:**

- [x] The validate CLI accepts version-1 data/train/infer configs with explicit engine and kind-specific fields; reject bad versions, unknown/duplicate keys, unsafe YAML, and oversized input.
- [x] Duplicate ids, unresolved inputs/outputs, and cycles are rejected within configured input-size limits.
- [x] Validation performs no connector calls or credential resolution; only an explicitly requested report is written.

**Verification:**

```sh
python3 -m pytest tests/unit/core/test_config.py tests/contract/core/test_validate_cli.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T003

**Files likely touched:**

- `src/gmldf/core/config.py`
- `src/gmldf/__main__.py`
- `tests/unit/core/test_config.py`
- `tests/contract/core/test_validate_cli.py`
- `docs/configuration.md`

**Estimated scope:** Medium (5 files).

**Evidence (2026-11-05):** T004a/b/c completed with tests written RED before behavior. Strict model, safe YAML/reference, offline CLI/report, and near-limit profile-override regression tests pass. Full suite: 71 tests. Ruff/build passed; editable installation and standard-pip wheel installation in a clean base-only environment succeeded. Reports explicitly leave backend capabilities unchecked.

**Review follow-up:** Fixed scalar-constructor exception normalization and raw YAML parser traceback exposure. Fifteen regressions failed before the fix and pass afterward, covering Python tracebacks/logging and CLI exit/error output; full suite now passes 86 tests.


<a id="t005"></a>

### [x] T005: Define serializable run and artifact contracts

**Description:** Deliver this core-contracts capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-core-contracts.md](../SPEC-core-contracts.md)

**Acceptance criteria:**

- [x] DatasetRef, ArtifactRef, RunContext, TrainingResult, PredictionResult, and write/run receipts have explicit fields and stable JSON forms.
- [x] Opaque dataframe/model handles stay out of serialized manifests; preserve metric direction, resolved search/default versions, evaluated/refitted/returned model references, and fit-data cutoffs.
- [x] Errors carry safe codes/field paths, chained internal causes, and retry safety; terminal states include UTC timestamps.

**Verification:**

```sh
python3 -m pytest tests/contract/core/test_types.py tests/unit/core/test_errors.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T004

**Files likely touched:**

- `src/gmldf/core/types.py`
- `src/gmldf/core/errors.py`
- `tests/contract/core/test_types.py`
- `tests/unit/core/test_errors.py`

**Estimated scope:** Medium (4 files).

**Evidence (2026-11-05):** T005a safe errors; T005b metadata/evaluated-refit contracts; T005c context/run/write receipts. New contracts failed before implementation. Strict-version/URI and output-commit/event regressions reproduced and fixed. 47 new tests (133 total) pass, as do Ruff/format/build. Message, assessment-attribution and retry-uncertainty mutations were caught; restored source rechecked. Independent five-axis review found no remaining actionable issues. Simplification removed only a redundant refit comparison, separately verified. See docs/contracts.md. No backend execution/support is implied.

<a id="t006"></a>

### [x] T006: Reject unsupported or denied work before access

**Description:** Deliver this core-contracts capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-core-contracts.md](../SPEC-core-contracts.md)

**Acceptance criteria:**

- [x] Unknown/unsupported combinations and denied source/operation/output/runtime policies fail before any provider access.
- [x] Lazy credential references resolve only at access time; secrets in URLs, context, and exception chains are absent from public output.
- [x] Capability statuses distinguish planned, verified, and unsupported; missing optional dependencies give actionable errors.

**Verification:**

```sh
python3 -m pytest tests/unit/core/test_preflight.py tests/unit/core/test_secrets.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T005

**Files likely touched:**

- `src/gmldf/core/capabilities.py`
- `src/gmldf/core/policy.py`
- `src/gmldf/core/secrets.py`
- `tests/unit/core/test_preflight.py`
- `tests/unit/core/test_secrets.py`

**Estimated scope:** Medium (5 files).

**Evidence (2026-11-05):** T006a lazy credentials/public diagnostics; T006b controlled dependency remedies; T006c exact capability and policy preflight. 33 added tests (166 total) pass. Missing modules/APIs and review regressions failed RED before fixes. Review fixed URI leakage/aggregate bounds, full operation policy coverage, format/transfer routes and prediction output provenance. Re-review has no actionable findings. Redaction/status mutations caught; source restored and checks rerun. Ruff/format/build pass. Registry fakes establish semantics only; no backend/platform support is claimed from them.

### Checkpoint C02: After T004, T005, T006

- [x] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [x] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [x] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 03: T087, T007, T008

<a id="t087"></a>

### [x] T087: Require explicit ML intent in config

**Description:** Make the confirmed explicit engine/task/algorithms/metric rules and safe refit/transfer defaults observable before model execution.

**Spec:** [SPEC-core-contracts.md](../SPEC-core-contracts.md)

**Acceptance criteria:**

- [x] Missing engine/task/metric, empty/duplicate candidate lists, and invalid candidate/task/metric declarations produce exact field-path errors.
- [x] Unspecified refit and cross-engine transfer flags are false; enabled transfers require supported source/target and positive row/byte limits.
- [x] Registry tests prove no task/engine inference, installed-algorithm scan, unlisted-baseline insertion, or silent algorithm-variant substitution.

**Verification:**

```sh
python3 -m pytest tests/contract/core/test_explicit_ml_config.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T004, T006

**Files likely touched:**

- `src/gmldf/core/config.py`
- `tests/contract/core/test_explicit_ml_config.py`
- `docs/configuration.md`

**Estimated scope:** Medium (3 files).

**Evidence (2026-11-05):** T087a strict duplicate/task-metric/direction checks and disabled transfer object; T087b exact provider rejection paths and registry proofs. New failures reproduced RED before fixes;26 explicit-intent tests/192 total pass. Invalid candidate/task/engine combinations fail at candidate names; enabled transfers require bounds, matching processing source and an exact supported route. Only requested candidates are looked up; unlisted baseline dependencies remain untouched. Independent review has no actionable findings; mutation checks caught duplicate guard and path regressions. Ruff/format/build pass; no further simplification justified. No model/provider execution claimed.

<a id="t007"></a>

### [x] T007: Read a schema-checked local CSV

**Description:** Deliver this data-io capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [x] CSV reads honor declared encoding, delimiter, nulls, column types, and date parsing.
- [x] Malformed rows, schema mismatch, and missing files produce safe distinct errors; fixtures cover empty/Unicode/decimal/date values.
- [x] Read results expose engine/schema/source identity without hidden conversion; pandas is an optional backend dependency.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_csv_read.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T006

**Files likely touched:**

- `src/gmldf/data_io/base.py`
- `src/gmldf/data_io/csv.py`
- `tests/contract/data_io/test_csv_read.py`
- `pyproject.toml`

**Estimated scope:** Medium (4 files).

**Evidence (2026-11-05):** T007a private dataset handle; T007b real pandas strict CSV reader; T007c usage/profile documentation.30 CSV contract tests plus core contracts give223 total passing tests. Encoding/delimiter/nulls/types/date/timestamp/decimal/empty/Unicode and safe distinct failure cases are covered; denied access opens no source. RED preceded implementation and all review fixes; row-width mutation caught. Independent re-review has no actionable findings. Separate simplification removed redundant UnicodeError catch;30 unchanged tests, Ruff/format/build pass. Pinned optional extra installed successfully; reader import remains backend-lazy. Source snapshot/version intentionally unknown. Documented YAML validated after quoting its literal NULL token.

<a id="t008"></a>

### [x] T008: Apply the example's stateless pandas steps

**Description:** Deliver this processing capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [x] Select, cast, and sort operate on named inputs with explicit null/type/time/ordering behavior.
- [x] Unknown operation names and incompatible engine handles fail without eval, arbitrary imports, or collection.
- [x] Expected-value fixtures cover empty data, invalid casts, ordering, and temporal types.

**Verification:**

```sh
python3 -m pytest tests/contract/processing/test_pandas_basic.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T007

**Files likely touched:**

- `src/gmldf/processing/base.py`
- `src/gmldf/processing/pandas.py`
- `tests/contract/processing/test_pandas_basic.py`

**Estimated scope:** Medium (3 files).

**Evidence (2026-11-05):** Real pandas select/cast/sort implements the existing transform provider signature.23 focused tests/248 total pass, including named chaining, empty frames, copied inputs, stable multikey/null order, strict numeric/temporal behavior, unsupported handles/operations and authorization of all steps before processing. Missing module reproduced RED; finite-guard mutation caught5 failures. Independent review has no actionable findings; no simplification justified. Ruff/format/build and documented YAML checks pass. Other operations/engines remain incomplete; this is not a release milestone.

### Checkpoint C03: After T087, T007, T008

- [x] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [x] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [x] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 04: T009, T010, T011

<a id="t009"></a>

### [x] T009: Publish local CSV results safely

**Description:** Deliver this data-io capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [x] Default error_if_exists preserves an existing destination; explicit overwrite affects only that destination.
- [x] Atomic local publish is tested under injected failure and returns a truthful commit/retry receipt.
- [x] Append/upsert are rejected until their semantics are supported; ambiguous commits are never blindly retried.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_csv_write.py tests/unit/data_io/test_local_publish.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T007

**Files likely touched:**

- `src/gmldf/data_io/csv.py`
- `src/gmldf/data_io/local_publish.py`
- `tests/contract/data_io/test_csv_write.py`
- `tests/unit/data_io/test_local_publish.py`

**Estimated scope:** Medium (4 files).

**Evidence (2026-11-05):** T009a atomic local publisher; T009b typed pandas CSV writer; T009c usage/evidence.13 CSVwriter and9 publisher cases pass (270 total), covering existing/concurrent destination preservation, explicit overwrite, serialization/precommit/ambiguous/postcommit failures, safe receipts, row-count truthfulness, null-token collisions, empty/Unicode/decimal/boolean/UTF16/UTC round trips and denied/unsupported writes. RED preceded implementation and review fixes (row counts/nonmidnight dates). Independent re-review clean; mode/date mutations caught failures and restored. Shared framing/path extraction was separately verified with32 unchanged reader tests. No further simplification justified. Ruff/format/build and documented YAML validate. Atomic visibility is verified; crash durability, source-version linkage and cancellation recovery remain later tasks.

<a id="t010"></a>

### [x] T010: Run a data-only workflow through providers

**Description:** Deliver this workflow capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-workflow.md](../SPEC-workflow.md)

**Acceptance criteria:**

- [x] A validated data config executes source → steps → output in dependency order using provider-owned interfaces.
- [x] Failed dependencies skip consumers and retain completed receipts; required output failure makes the run fail.
- [x] Data-only execution imports no AutoML library; workflow never imports runtime implementations.

**Verification:**

```sh
python3 -m pytest tests/contract/workflow/test_data_run.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T008, T009

**Files likely touched:**

- `src/gmldf/workflow/runner.py`
- `src/gmldf/workflow/providers.py`
- `tests/contract/workflow/test_data_run.py`

**Estimated scope:** Medium (3 files).

**Evidence:**20 workflow contracts and299 full-suite tests pass on the pinned local profile; Ruff/format/build pass. Receipt attribution finding reproduced/fixed/re-reviewed; dependency-skip mutation detected. See docs/workflow.md. No train/infer, cancellation, recovery or external compatibility claim.

<a id="t011"></a>

### [x] T011: Expose local workflow execution

**Description:** Deliver this execution capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-execution.md](../SPEC-execution.md)

**Acceptance criteria:**

- [x] run accepts config/profile/run-id/output-dir and emits the same result as the library, with progress on stderr.
- [x] Exit codes distinguish success, rejection, failure, and confirmed cancellation.
- [x] Paths resolve relative to the config; completed run-id reuse or config mismatch fails without output mutation.

**Verification:**

```sh
python3 -m pytest tests/contract/execution/test_local_cli.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T010

**Files likely touched:**

- `src/gmldf/__main__.py`
- `src/gmldf/execution/local.py`
- `tests/contract/execution/test_local_cli.py`

**Estimated scope:** Medium (3 files).

**Evidence:**16 local CLI contract cases,315 full-suite tests, Ruff/format/build pass. Review fixes and reservedmetadata mutation verified; separate provider-enumeration simplification rechecked with33 affected tests. No unresolved findings.130 mapping verified; actual worker cancellation remains T031. Run-ID namespace is output-dir/run-id.

### Checkpoint C04: After T009, T010, T011

- [x] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [x] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [x] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 05: T012, T013, T014

<a id="t012"></a>

### [x] T012: Prove the complete CSV data path

**Description:** Deliver this recipes capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-recipes.md](../SPEC-recipes.md)

**Acceptance criteria:**

- [x] A fresh local install reads the synthetic CSV, applies configured steps, and writes the expected output without source edits.
- [x] Changing input/output paths needs config changes only; invalid config produces no business output.
- [x] Quickstart uses actual implemented commands and states supported behavior accurately.

**Verification:**

```sh
python3 -m pytest tests/e2e/test_data_only.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T011

**Files likely touched:**

- `examples/data-only/workflow.yaml`
- `examples/data-only/input.csv`
- `tests/e2e/test_data_only.py`
- `docs/quickstart.md`

**Estimated scope:** Medium (4 files).

**Evidence:**4 real clean-install e2e cases/319 full tests, Ruff/format/build pass. Fresh standardpip wheel/runtime and devbuild verified offline from prepared dependency wheels. Missing Hatchling devdependency reproduced/fixed/re-reviewed. No unresolved findings or skipped checks. See docs/quickstart.md and docs/development.md.

<a id="t013"></a>

### [x] T013: Add a Parquet round trip

**Description:** Deliver this data-io capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [x] CSV and Parquet variants yield equivalent declared values/schema for synthetic example records.
- [x] Parquet uses the existing read/write receipts and local atomic publish behavior.
- [x] The selected optional Parquet dependency/version is pinned in the local environment profile.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_parquet.py tests/e2e/test_data_formats.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T012

**Files likely touched:**

- `src/gmldf/data_io/parquet.py`
- `tests/contract/data_io/test_parquet.py`
- `tests/e2e/test_data_formats.py`
- `pyproject.toml`

**Estimated scope:** Medium (4 files).

**Evidence:**26 nativeParquet contracts,4 CSV/Parquet workflow permutations, cleanCSV-only missingextra rejection/356 total tests; Ruff/format/build pass. PinnedPyArrow26.0.1 installed locally. Storage-dependentNaN, awaredate drift and nullability findings reproduced/fixed/re-reviewed; guardmutations detected. No unresolved findings, skippedchecks or externalhost claims.

<a id="t014"></a>

### [x] T014: Validate one forecasting acceptance fixture

**Description:** Create a synthetic temporal case that exercises the generic forecasting contract without defining library-wide defaults.

**Spec:** [SPEC-recipes.md](../SPEC-recipes.md)

**Acceptance criteria:**

- [x] Deterministic synthetic daily data matches the approved date range/cutoffs and contains no copied/customer data.
- [x] Duplicate/missing dates, non-finite targets, invalid frequency, and nonpositive horizons fail explicitly.
- [x] Time ordering, validation/test windows, and origin dates are verified from known expected records.

**Verification:**

```sh
python3 -m pytest tests/unit/automl/test_forecast_data.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T013

**Files likely touched:**

- `src/gmldf/automl/forecast_data.py`
- `tests/fixtures/automl/sales.csv`
- `tests/unit/automl/test_forecast_data.py`
- `docs/forecasting-fixture.md`

**Estimated scope:** Medium (4 files).

**Evidence:**27 forecastdata tests/383 full tests and required checks pass. Deterministic731-row syntheticfixture,675/28/28 windows and alternate2hour/customcolumncase verified. Missingmodule and3 boundaryfailures reproduced/fixed; complete-gridmutation detected; independentreviewclean. See docs/forecasting-fixture.md; fitting remains T015 onward.

### Checkpoint C05: After T012, T013, T014

- [x] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [x] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [x] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 06: T015, T016, T086

<a id="t015"></a>

### [x] T015: Evaluate a causal baseline forecast

**Description:** Deliver this automl capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [x] The explicitly listed naive candidate uses configured temporal cutoffs and sees training targets only; no baseline is inserted when not listed.
- [x] MAE is recomputable and exactly horizon predictions have ordered expected timestamps.
- [x] Baseline results use core result contracts and include split identity, metric direction, seed, and fit accounting.

**Verification:**

```sh
python3 -m pytest tests/contract/automl/test_baseline.py -q
```

- [x] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T014, T087

**Files likely touched:**

- `src/gmldf/automl/forecasting.py`
- `src/gmldf/automl/candidates/naive.py`
- `tests/contract/automl/test_baseline.py`

**Estimated scope:** Medium (3 files).

**Evidence:**17 native naive-state tests and15 baselineevaluation contracts/421 full tests, Ruff/format/build pass. Onlylisted/policy/cutoff/MAE/seed/fit/split evidence and heldouttarget independence verified. Prediction-score and JSONprecision regressions fixed; fit-leakage mutation detected5 failures. Independentreviewclean. No boundedsearch, workerlimits, fullTrainingResult or durableartifact claim (later tasks).

<a id="t016"></a>

### [ ] T016: Fit an ARIMA forecasting candidate

**Description:** Deliver this automl capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] The explicitly listed ARIMA candidate validates task/parameter compatibility; omitted ranges will resolve through the default-space provider.
- [ ] Real library fits forecast from the origin without held-out target access and preserve the candidate persistence handle.
- [ ] Fit/convergence failures are safe candidate failures; dependency/version requirements are recorded.

**Verification:**

```sh
python3 -m pytest tests/contract/automl/test_arima.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T015

**Files likely touched:**

- `src/gmldf/automl/candidates/arima.py`
- `tests/contract/automl/test_arima.py`
- `pyproject.toml`

**Estimated scope:** Medium (3 files).

<a id="t086"></a>

### [ ] T086: Resolve versioned default tuning domains

**Description:** Supply per-algorithm default search ranges without expanding the configured candidate list.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] Every supported listed algorithm resolves omitted domains from versioned library defaults; valid per-key overrides and fixed values are preserved.
- [ ] Unknown keys, invalid types/ranges, incompatible task/metric pairs, and unbounded search limits fail before fitting.
- [ ] Resolved spaces/default versions appear in results, and a newly installed/unlisted algorithm never enters search.

**Verification:**

```sh
python3 -m pytest tests/unit/automl/test_default_spaces.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T016, T087

**Files likely touched:**

- `src/gmldf/automl/default_spaces.py`
- `tests/unit/automl/test_default_spaces.py`
- `docs/tuning.md`

**Estimated scope:** Medium (3 files).

### Checkpoint C06: After T015, T016, T086

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 07: T017, T018, T019

<a id="t017"></a>

### [ ] T017: Select models with a bounded validation search

**Description:** Deliver this automl capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] Search uses only explicit algorithm ids and their resolved supported domains; the cap counts a baseline only if listed.
- [ ] Ranking uses finite validation scores, metric direction, and declared tie order; test scores cannot alter selection.
- [ ] Installed/unlisted algorithms and baselines never fit; listed baselines can win, failures stay visible, and no completed candidate yields no winner.

**Verification:**

```sh
python3 -m pytest tests/unit/automl/test_search.py tests/unit/automl/test_selection.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T016, T086

**Files likely touched:**

- `src/gmldf/automl/search.py`
- `src/gmldf/automl/selection.py`
- `tests/unit/automl/test_search.py`
- `tests/unit/automl/test_selection.py`

**Estimated scope:** Medium (4 files).

<a id="t018"></a>

### [ ] T018: Enforce training deadlines and cancellation

**Description:** Deliver this automl capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] Expiry prevents new fits and supported workers stop on cancellation/deadline, including refit/test stages.
- [ ] Controlled-clock tests distinguish candidate failures from fatal policy/auth/shared-data failures.
- [ ] Unsupported enforcement modes fail preflight instead of promising a timeout they cannot enforce.

**Verification:**

```sh
python3 -m pytest tests/unit/automl/test_limits.py tests/integration/automl/test_worker_stop.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T017

**Files likely touched:**

- `src/gmldf/automl/workers.py`
- `src/gmldf/automl/search.py`
- `tests/unit/automl/test_limits.py`
- `tests/integration/automl/test_worker_stop.py`

**Estimated scope:** Medium (4 files).

<a id="t019"></a>

### [ ] T019: Preserve the evaluated selected pipeline

**Description:** Keep validation selection and untouched assessment attached to the exact evaluated artifact, independently of optional later refit.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] The validation winner is refitted on train+validation, then assessed once on the test window.
- [ ] Mutating test targets changes assessment only, never chosen candidate/parameters; future targets cannot change earlier features.
- [ ] TrainingResult identifies the same refitted pipeline, cutoff, feature signature, predictions, and separately counted refit.

**Verification:**

```sh
python3 -m pytest tests/contract/automl/test_refit_assessment.py tests/unit/automl/test_leakage.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T018

**Files likely touched:**

- `src/gmldf/automl/forecasting.py`
- `tests/contract/automl/test_refit_assessment.py`
- `tests/unit/automl/test_leakage.py`

**Estimated scope:** Medium (3 files).

### Checkpoint C07: After T017, T018, T019

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 08: T021, T022, T085

<a id="t021"></a>

### [ ] T021: Publish complete local model bundles

**Description:** Deliver this model-lifecycle capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-model-lifecycle.md](../SPEC-model-lifecycle.md)

**Acceptance criteria:**

- [ ] Bundle manifests include immutable evaluated/refitted identity, signature, resolved search/default versions, fit cutoff, provenance, metrics, and trial evidence.
- [ ] Atomic publish exposes only complete bundles; incomplete/corrupt writes are rejected.
- [ ] Core TrainingResult is consumed without importing the AutoML orchestration implementation.

**Verification:**

```sh
python3 -m pytest tests/contract/model_lifecycle/test_local_store.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T005, T009

**Files likely touched:**

- `src/gmldf/model_lifecycle/bundles.py`
- `src/gmldf/model_lifecycle/local.py`
- `tests/contract/model_lifecycle/test_local_store.py`

**Estimated scope:** Medium (3 files).

<a id="t022"></a>

### [ ] T022: Load trusted forecasting pipelines

**Description:** Deliver this model-lifecycle capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-model-lifecycle.md](../SPEC-model-lifecycle.md)

**Acceptance criteria:**

- [ ] Naive and ARIMA bundles reload with matching predictions within approved tolerance and unchanged feature/cutoff identity.
- [ ] Untrusted origins, missing preprocessing, incompatible dependencies/signatures, and checksum errors fail before deserialization; evaluation scores identify only the evaluated artifact.
- [ ] Checksums are not treated as a trust decision; no hidden refit occurs on load or invalid inference input.

**Verification:**

```sh
python3 -m pytest tests/contract/model_lifecycle/test_roundtrip.py tests/unit/model_lifecycle/test_trust.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T021, T019

**Files likely touched:**

- `src/gmldf/model_lifecycle/serializers.py`
- `src/gmldf/model_lifecycle/predictor.py`
- `tests/contract/model_lifecycle/test_roundtrip.py`
- `tests/unit/model_lifecycle/test_trust.py`

**Estimated scope:** Medium (4 files).

<a id="t085"></a>

### [ ] T085: Refit the selected pipeline only when configured

**Description:** Implement the confirmed optional full-data refit while preserving evaluated model identity and assessment evidence.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] Default false returns the evaluated model; true fits only the selected configuration on all eligible supplied training-run data and returns a distinct refitted model.
- [ ] Retain both immutable artifact identities and the original report; scores never imply refitted performance, and forecast cutoffs reflect each artifact's fitted data.
- [ ] Requested refit obeys the same overall deadline, fails visibly if incomplete, and never triggers another search or ordinary-inference refit.

**Verification:**

```sh
python3 -m pytest tests/contract/automl/test_refit.py tests/e2e/test_refit.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T019, T022

**Files likely touched:**

- `src/gmldf/automl/refit.py`
- `src/gmldf/model_lifecycle/bundles.py`
- `tests/contract/automl/test_refit.py`
- `tests/e2e/test_refit.py`

**Estimated scope:** Medium (4 files).

### Checkpoint C08: After T021, T022, T085

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 09: T020, T023, T024

<a id="t020"></a>

### [ ] T020: Compose a training workflow

**Description:** The fake is confined to tests; the production path requires a real supplied lifecycle provider and never reports success with a stub.

**Spec:** [SPEC-workflow.md](../SPEC-workflow.md)

**Acceptance criteria:**

- [ ] Training uses the explicit engine/task/candidates/metric, then exports predictions and distinct evaluated/optional-refit references through core contracts.
- [ ] Model lifecycle is invoked through its declared interface using a contract fake until the concrete store is ready.
- [ ] Mandatory assessment/save/output failures prevent a successful run; unsupported ML config fails before reads.

**Verification:**

```sh
python3 -m pytest tests/contract/workflow/test_training.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T019, T011, T085

**Files likely touched:**

- `src/gmldf/workflow/runner.py`
- `src/gmldf/workflow/providers.py`
- `tests/contract/workflow/test_training.py`

**Estimated scope:** Medium (3 files).

<a id="t023"></a>

### [ ] T023: Run inference from an immutable bundle

**Description:** Deliver this workflow capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-workflow.md](../SPEC-workflow.md)

**Acceptance criteria:**

- [ ] Inference loads the chosen immutable pipeline, validates feature input, and writes predictions without any fit call.
- [ ] Forecasting emits the requested horizon from the selected artifact's actual fit cutoff; evaluated and optional full-data-refitted models can have different origins.
- [ ] Missing model/features, cancelled work, and required output failures produce truthful run states.

**Verification:**

```sh
python3 -m pytest tests/contract/workflow/test_inference.py tests/unit/workflow/test_feature_signature.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T022, T020

**Files likely touched:**

- `src/gmldf/workflow/runner.py`
- `tests/contract/workflow/test_inference.py`
- `tests/unit/workflow/test_feature_signature.py`

**Estimated scope:** Medium (3 files).

<a id="t024"></a>

### [ ] T024: Deliver the local forecasting recipe

**Description:** Deliver this recipes capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-recipes.md](../SPEC-recipes.md)

**Acceptance criteria:**

- [ ] Complete forecast train/infer configs explicitly choose engine/task/algorithms/metric and retain immutable evaluated/refitted identities without source edits.
- [ ] CSV/Parquet variants match within 1e-6 relative/absolute tolerance, with leaderboard, baseline, metrics, manifest, and predictions.
- [ ] Saved MAE and 28-date windows are independently recomputable; future inference follows the approved artifact cutoff.

**Verification:**

```sh
python3 -m pytest tests/e2e/test_forecasting.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T023, T013

**Files likely touched:**

- `examples/forecasting/workflow.yaml`
- `examples/forecasting/inference.yaml`
- `tests/e2e/test_forecasting.py`
- `docs/forecasting.md`

**Estimated scope:** Medium (4 files).

### Checkpoint C09: After T020, T023, T024

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 10: T025, T026, T027

<a id="t025"></a>

### [ ] T025: Harden workflow failure and retry semantics

**Description:** Deliver this workflow capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-workflow.md](../SPEC-workflow.md)

**Acceptance criteria:**

- [ ] Injected failures at every stage skip dependants and preserve committed/partial output receipts.
- [ ] Completed run-id/config reuse and ambiguous append retries are blocked; multiple sinks never imply a transaction.
- [ ] Cancellation is terminal only when work actually stops; missing required tracking/artifact completion cannot masquerade as success.

**Verification:**

```sh
python3 -m pytest tests/unit/workflow/test_failure_matrix.py tests/contract/workflow/test_retries.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T024

**Files likely touched:**

- `src/gmldf/workflow/state.py`
- `src/gmldf/workflow/runner.py`
- `tests/unit/workflow/test_failure_matrix.py`
- `tests/contract/workflow/test_retries.py`

**Estimated scope:** Medium (4 files).

<a id="t026"></a>

### [ ] T026: Record safe, useful run events

**Description:** Deliver this core-contracts capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-core-contracts.md](../SPEC-core-contracts.md)

**Acceptance criteria:**

- [ ] Stage/trial/output events carry timestamps, durations, identities, progress, safe reasons, and completion states.
- [ ] Sentinel secrets in URLs, provider exceptions, manifests, and CLI output are redacted; raw records are excluded by default.
- [ ] Events retain enough provenance to distinguish config, code, environment, dataset version, and runtime.

**Verification:**

```sh
python3 -m pytest tests/contract/core/test_events.py tests/e2e/test_redaction.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T025

**Files likely touched:**

- `src/gmldf/core/events.py`
- `src/gmldf/workflow/runner.py`
- `tests/contract/core/test_events.py`
- `tests/e2e/test_redaction.py`

**Estimated scope:** Medium (4 files).

<a id="t027"></a>

### [ ] T027: Verify a clean local installation milestone

**Description:** Pin one tested local environment and exercise the implemented paths; this milestone alone does not complete first-release scope.

**Spec:** [SPEC-recipes.md](../SPEC-recipes.md)

**Acceptance criteria:**

- [ ] A clean environment builds/installs the pinned example profile and runs data/train/infer from documented commands.
- [ ] Base-install import isolation and full negative acceptance scenarios pass without cloud credentials.
- [ ] Evidence marks only exercised combinations verified; business accuracy is not inferred from synthetic data.

**Verification:**

```sh
python3 -m pytest tests/e2e/test_clean_install.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T026

**Files likely touched:**

- `tests/e2e/test_clean_install.py`
- `docs/quickstart.md`
- `docs/compatibility.md`
- `requirements/local.txt`

**Estimated scope:** Medium (4 files).

### Checkpoint C10: After T025, T026, T027

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 11: T028, T029, T030

<a id="t028"></a>

### [ ] T028: Demonstrate user-owned container invocation

**Description:** Provide a reproducible example that invokes the installed library inside a user-launched container; no image publishing or launch management is added to the library.

**Spec:** [SPEC-execution.md](../SPEC-execution.md)

**Acceptance criteria:**

- [ ] A generic example image invokes the same installed Python/CLI package with read-only config and writable durable outputs.
- [ ] Image identity/dependency profile is recorded; secrets/customer inputs/build caches are excluded.
- [ ] A user-launched local container smoke test verifies the supported invocation and resource ownership.

**Verification:**

```sh
python3 -m pytest tests/integration/execution/test_container.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T027, T002

**Files likely touched:**

- `examples/environments/container/Dockerfile`
- `.dockerignore`
- `tests/integration/execution/test_container.py`
- `docs/container.md`

**Estimated scope:** Medium (4 files).

<a id="t029"></a>

### [ ] T029: Accept an existing host context

**Description:** Define current-process context injection and ownership for sessions, credential references, outputs, limits, and cancellation.

**Spec:** [SPEC-execution.md](../SPEC-execution.md)

**Acceptance criteria:**

- [ ] Python callers may pass an existing engine session and compatible host context without notebook globals.
- [ ] Host-owned resources are not unexpectedly stopped or reconfigured; library-owned resources are cleaned up.
- [ ] Context/capability validation performs no remote launch, provisioning, or silent engine selection.

**Verification:**

```sh
python3 -m pytest tests/unit/execution/test_host_context.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T011, T002

**Files likely touched:**

- `src/gmldf/execution/context.py`
- `tests/unit/execution/test_host_context.py`
- `docs/python-api.md`

**Estimated scope:** Medium (3 files).

<a id="t030"></a>

### [ ] T030: Expose the public Python invocation API

**Description:** Share one validation/provider/workflow path between Python callers and the existing local CLI.

**Spec:** [SPEC-execution.md](../SPEC-execution.md)

**Acceptance criteria:**

- [ ] run(config, context=...) accepts the documented config inputs and returns the same RunResult as CLI execution.
- [ ] Missing extras, invalid config, unsupported combinations, and library failures retain the same structured semantics.
- [ ] The public API/CLI exposes no remote submit, job-status, or remote cancel operations.

**Verification:**

```sh
python3 -m pytest tests/contract/execution/test_python_api.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T029, T023

**Files likely touched:**

- `src/gmldf/__init__.py`
- `src/gmldf/execution/api.py`
- `src/gmldf/__main__.py`
- `tests/contract/execution/test_python_api.py`

**Estimated scope:** Medium (4 files).

### Checkpoint C11: After T028, T029, T030

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 12: T031, T032, T033

<a id="t031"></a>

### [ ] T031: Honor process cancellation and resource ownership

**Description:** Propagate deadlines/cancellation for this library invocation without managing the external platform's jobs.

**Spec:** [SPEC-execution.md](../SPEC-execution.md)

**Acceptance criteria:**

- [ ] Python/CLI cancellation and deadlines stop supported library-owned workers before reporting cancelled.
- [ ] Caller-owned sessions survive cancellation/failure and shared providers receive safe deadline context.
- [ ] No job-management SDK calls are made; externally launched job lifecycle remains the caller's responsibility.

**Verification:**

```sh
python3 -m pytest tests/contract/execution/test_process_cancellation.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T030, T018

**Files likely touched:**

- `src/gmldf/execution/context.py`
- `src/gmldf/execution/local.py`
- `tests/contract/execution/test_process_cancellation.py`

**Estimated scope:** Medium (3 files).

<a id="t032"></a>

### [ ] T032: Verify user-launched Kubernetes invocation

**Description:** Exercise the pip-installed library inside an existing user-managed container workload; the library does not create or control the job.

**Spec:** [SPEC-recipes.md](../SPEC-recipes.md)

**Acceptance criteria:**

- [ ] Local container and user-launched Kubernetes use the same image/data/config/seed and match supported example output within tolerance.
- [ ] Outputs persist outside the process; library-owned deadlines/cancellation behave as declared.
- [ ] Record host/image/installation evidence and confirm library calls make no provisioning or job-management requests.

**Verification:**

```sh
python3 -m pytest tests/e2e/test_portability.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Environment gate: an existing authorized test host and user-managed launch are required; no cluster creation, SDK submission, or registry publishing is implied.

**Dependencies:** T028, T031

**Files likely touched:**

- `tests/e2e/test_portability.py`
- `examples/environments/kubernetes/job.yaml`
- `docs/evidence/kubernetes-invocation.md`

**Estimated scope:** Medium (3 files).

<a id="t033"></a>

### [ ] T033: Review the first integrated development milestone

**Description:** Review currently completed data/forecast/save/load/host paths without presenting this subset as the library's first release.

**Spec:** [SPEC-recipes.md](../SPEC-recipes.md)

**Acceptance criteria:**

- [ ] Trace completed milestone behavior to passing evidence and retain incomplete connector/engine/task requirements.
- [ ] Implemented data/train/infer examples and safe-failure checks run without source edits.
- [ ] Review records milestone progress only; first-release acceptance still requires all named capabilities and all four task families.

**Verification:**

```sh
python3 -m pytest tests/unit tests/contract tests/e2e/test_data_only.py tests/e2e/test_forecasting.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T032

**Files likely touched:**

- `docs/evidence/development-milestone.md`
- `docs/quickstart.md`
- `docs/compatibility.md`
- `tasks/todo.md`

**Estimated scope:** Medium (4 files).

### Checkpoint C12: After T031, T032, T033

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 13: T034, T035, T036

<a id="t034"></a>

### [ ] T034: Specify common transformation semantics

**Description:** Keep existing implemented-backend tests passing; newly defined cases are consumed when each backend lands, not added as skipped tests.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [ ] Contract cases define null filtering/join keys, duplicate keys, ordering, time zones, decimal precision, casts, and empty data.
- [ ] Each common operation has expected values/schema or an explicit unsupported case.
- [ ] Contract cases avoid engine-specific expressions and provide the comparison rules needed for parity.

**Verification:**

```sh
python3 -m pytest tests/contract/processing -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T008

**Files likely touched:**

- `docs/processing-semantics.md`
- `tests/contract/processing/cases.py`
- `tests/fixtures/processing/edge_cases.json`

**Estimated scope:** Medium (3 files).

<a id="t035"></a>

### [ ] T035: Extend pandas row transformations

**Description:** Deliver this processing capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [ ] Rename, filter, and constant-fill implement the declared contract and parameter validation.
- [ ] Null predicates, missing columns, type errors, and explicit ordering match shared cases.
- [ ] Only approved operations dispatch; no backend-specific SQL is claimed portable.

**Verification:**

```sh
python3 -m pytest tests/contract/processing/test_pandas_rows.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T034

**Files likely touched:**

- `src/gmldf/processing/pandas.py`
- `tests/contract/processing/test_pandas_rows.py`

**Estimated scope:** Small (2 files).

<a id="t036"></a>

### [ ] T036: Support pandas joins and aggregates

**Description:** Deliver this processing capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [ ] Configured named-input joins and grouped aggregates use explicit keys, join type, aggregation, and schema.
- [ ] Duplicate/null join keys, empty groups, decimal precision, and unspecified row order match shared cases.
- [ ] Unsupported operation/type pairs reject before output publication.

**Verification:**

```sh
python3 -m pytest tests/contract/processing/test_pandas_relational.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T035

**Files likely touched:**

- `src/gmldf/processing/pandas.py`
- `tests/contract/processing/test_pandas_relational.py`

**Estimated scope:** Small (2 files).

### Checkpoint C13: After T034, T035, T036

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 14: T037, T038, T039

<a id="t037"></a>

### [ ] T037: Build causal forecasting features

**Description:** Deliver this processing capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [ ] Configured lags/rolling features observe prior values only and respect series groups and cutoff.
- [ ] Mutating future targets cannot alter past features; missing-history behavior is explicit.
- [ ] Feature signatures preserve order/types and reject incompatible forecasting inputs.

**Verification:**

```sh
python3 -m pytest tests/contract/processing/test_causal_features.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T036, T019

**Files likely touched:**

- `src/gmldf/processing/forecast_features.py`
- `tests/contract/processing/test_causal_features.py`

**Estimated scope:** Small (2 files).

<a id="t038"></a>

### [ ] T038: Fit reusable preprocessing inside a training fold

**Description:** Choose only transformations needed by the classification example; feature selection can follow through the same contract.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [ ] Approved imputers/encoders/scalers/feature selectors fit only training rows and expose a stable persisted feature signature.
- [ ] Validation-only categories/extreme values do not affect statistics; inference uses stored policies and never refits.
- [ ] Serialization/reload preserves signature and transformed values; optional full-data refit learns a distinct preprocessing instance without mutating evaluated statistics.

**Verification:**

```sh
python3 -m pytest tests/contract/processing/test_fitted_preprocessing.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T036, T022

**Files likely touched:**

- `src/gmldf/processing/preprocessing.py`
- `tests/contract/processing/test_fitted_preprocessing.py`
- `pyproject.toml`

**Estimated scope:** Medium (3 files).

<a id="t039"></a>

### [ ] T039: Add Polars row operations

**Description:** Deliver this processing capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [ ] Select/rename/cast/filter/fill/sort pass the shared row-operation cases using real Polars.
- [ ] Optional import isolation and actionable missing-dependency errors hold.
- [ ] No conversion to pandas is used to conceal unsupported behavior.

**Verification:**

```sh
python3 -m pytest tests/contract/processing/test_polars_rows.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T035

**Files likely touched:**

- `src/gmldf/processing/polars.py`
- `tests/contract/processing/test_polars_rows.py`
- `pyproject.toml`

**Estimated scope:** Medium (3 files).

### Checkpoint C14: After T037, T038, T039

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 15: T040, T041, T042

<a id="t040"></a>

### [ ] T040: Add Polars relational operations

**Description:** Deliver this processing capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [ ] Join/group/aggregate pass shared relational cases with documented null/duplicate/type semantics.
- [ ] Schema and order comparisons use declared semantics rather than accidental backend output order.
- [ ] Unsupported operations remain explicitly unsupported in capability declarations.

**Verification:**

```sh
python3 -m pytest tests/contract/processing/test_polars_relational.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T039, T036

**Files likely touched:**

- `src/gmldf/processing/polars.py`
- `tests/contract/processing/test_polars_relational.py`

**Estimated scope:** Small (2 files).

<a id="t041"></a>

### [ ] T041: Add DuckDB row operations

**Description:** Deliver this processing capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [ ] Common row operations pass shared cases against real DuckDB relations.
- [ ] SQL translation uses validated identifiers/parameters and records its dialect.
- [ ] Engine-specific SQL requires explicit policy/capability and is not mislabeled portable.

**Verification:**

```sh
python3 -m pytest tests/contract/processing/test_duckdb_rows.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T035

**Files likely touched:**

- `src/gmldf/processing/duckdb.py`
- `tests/contract/processing/test_duckdb_rows.py`
- `pyproject.toml`

**Estimated scope:** Medium (3 files).

<a id="t042"></a>

### [ ] T042: Add DuckDB relational operations

**Description:** Deliver this processing capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [ ] Join/group/aggregate pass common cases without implicit pandas materialization.
- [ ] Decimals, null-key joins, duplicate keys, and ordering have the documented outcomes.
- [ ] Unsupported schema/type combinations produce actionable errors.

**Verification:**

```sh
python3 -m pytest tests/contract/processing/test_duckdb_relational.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T041, T036

**Files likely touched:**

- `src/gmldf/processing/duckdb.py`
- `tests/contract/processing/test_duckdb_relational.py`

**Estimated scope:** Small (2 files).

### Checkpoint C15: After T040, T041, T042

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 16: T043, T044, T045

<a id="t043"></a>

### [ ] T043: Add Spark row operations

**Description:** Deliver this processing capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [ ] Common row operations pass real Spark tests using a pinned supported Python/Java/Spark profile.
- [ ] No Spark/Databricks import is required by base or pandas installs.
- [ ] ANSI casts/time-zone differences are normalized where promised or recorded as unsupported.

**Verification:**

```sh
python3 -m pytest tests/integration/processing/test_spark_rows.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T035, T002

**Files likely touched:**

- `src/gmldf/processing/spark.py`
- `tests/integration/processing/test_spark_rows.py`
- `pyproject.toml`
- `requirements/spark.txt`

**Estimated scope:** Medium (4 files).

<a id="t044"></a>

### [ ] T044: Add Spark relational operations

**Description:** Deliver this processing capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [ ] Join/group/aggregate match declared shared cases on real Spark dataframes.
- [ ] No collect/toPandas occurs for relational work; schema/precision/null behavior is tested.
- [ ] Distributed order is treated as unspecified unless explicitly sorted.

**Verification:**

```sh
python3 -m pytest tests/integration/processing/test_spark_relational.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T043, T036

**Files likely touched:**

- `src/gmldf/processing/spark.py`
- `tests/integration/processing/test_spark_relational.py`

**Estimated scope:** Small (2 files).

<a id="t045"></a>

### [ ] T045: Allow only explicit bounded training transfers

**Description:** Implement the confirmed cross-engine ML boundary with safe supported routes; do not build every possible engine pair.

**Spec:** [SPEC-processing.md](../SPEC-processing.md)

**Acceptance criteria:**

- [ ] An explicit source/target route with positive row/byte limits is required; disabled/unlisted routes never materialize data.
- [ ] Unknown-size or oversized distributed-to-local requests reject before collection unless a bounded protocol can enforce both limits.
- [ ] Supported routes preserve schemas, record materialization, and allow otherwise compatible listed algorithms; unsafe requests never silently switch engine.

**Verification:**

```sh
python3 -m pytest tests/contract/processing/test_transfers.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T040, T042, T044

**Files likely touched:**

- `src/gmldf/processing/transfers.py`
- `tests/contract/processing/test_transfers.py`
- `tests/e2e/test_transfer.py`
- `docs/processing-semantics.md`

**Estimated scope:** Medium (4 files).

### Checkpoint C16: After T043, T044, T045

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 17: T046, T047, T048

<a id="t046"></a>

### [ ] T046: Implement explicit classification evaluation

**Description:** Provide a first-release classification protocol; synthetic examples choose their own metric/candidates rather than setting library-wide defaults.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] Validate an explicit classification task, compatible configured metric, and user algorithm list; no task/metric/candidate inference.
- [ ] Stratified holdout separates train/validation/test, validates labels/class support, and fits preprocessing only within training.
- [ ] Selection/refit/test reuses the existing metric-direction, budget, failure, and immutable-result contracts.

**Verification:**

```sh
python3 -m pytest tests/unit/automl/test_classification_protocol.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Record concrete candidate variants and assessment semantics as technical compatibility choices; users still explicitly configure task/candidates/metric.

**Dependencies:** T038, T017

**Files likely touched:**

- `src/gmldf/automl/classification.py`
- `tests/unit/automl/test_classification_protocol.py`
- `SPEC-automl.md`

**Estimated scope:** Medium (3 files).

<a id="t047"></a>

### [ ] T047: Fit scikit-learn classification candidates

**Description:** Deliver this automl capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] Explicitly listed baseline/estimator train and predict through existing candidate contracts with validated search spaces. Its default search domains are registered and overridable.
- [ ] Returned predictions/probabilities match metric requirements; invalid label/candidate pairs fail before fitting.
- [ ] Reloaded full pipelines preserve predictions and feature signature without test-set selection.

**Verification:**

```sh
python3 -m pytest tests/contract/automl/test_sklearn_classification.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T046, T018, T086

**Files likely touched:**

- `src/gmldf/automl/candidates/sklearn_classification.py`
- `tests/contract/automl/test_sklearn_classification.py`
- `src/gmldf/automl/default_spaces.py`

**Estimated scope:** Medium (3 files).

<a id="t048"></a>

### [ ] T048: Prove generic classification acceptance

**Description:** Classification is equal-status first-release scope, using the same public contracts as the other tasks.

**Spec:** [SPEC-recipes.md](../SPEC-recipes.md)

**Acceptance criteria:**

- [ ] Synthetic binary classification completes config-driven train/save/load/infer using existing public workflow/lifecycle contracts.
- [ ] Tests prove fold-local preprocessing and no inference fit calls, including an unseen-category case.
- [ ] Metrics, immutable bundle identities, failures, and any explicitly listed baseline appear in evidence without use-case-specific source edits.

**Verification:**

```sh
python3 -m pytest tests/e2e/test_classification.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T047, T024

**Files likely touched:**

- `examples/classification/workflow.yaml`
- `examples/classification/inference.yaml`
- `tests/e2e/test_classification.py`
- `docs/classification.md`

**Estimated scope:** Medium (4 files).

### Checkpoint C17: After T046, T047, T048

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 18: T049, T050, T051

<a id="t049"></a>

### [ ] T049: Implement explicit regression evaluation

**Description:** Provide regression assessment for the first release; example choices do not become implicit metric or algorithm defaults.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] Require an explicit regression task, compatible metric, and nonempty configured algorithm list.
- [ ] Numeric-target validation, holdout separation, metric direction, and test isolation use shared contracts.
- [ ] Non-finite labels/scores and mismatched candidate tasks fail explicitly.

**Verification:**

```sh
python3 -m pytest tests/unit/automl/test_regression_protocol.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Record small supported candidate variants and assessment details; do not infer user metric/task/algorithm choices.

**Dependencies:** T046

**Files likely touched:**

- `src/gmldf/automl/regression.py`
- `tests/unit/automl/test_regression_protocol.py`
- `SPEC-automl.md`

**Estimated scope:** Medium (3 files).

<a id="t050"></a>

### [ ] T050: Fit scikit-learn regression candidates

**Description:** Deliver this automl capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] Explicitly listed baseline/estimator tune through the shared trial budget and validation ranking. Its default search domains are registered and overridable.
- [ ] A synthetic oracle verifies selection remains unchanged when test targets change.
- [ ] Complete generic regression train/save/load/infer passes a synthetic end-to-end example within declared tolerance.

**Verification:**

```sh
python3 -m pytest tests/contract/automl/test_sklearn_regression.py tests/e2e/test_regression.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T049, T047, T086

**Files likely touched:**

- `src/gmldf/automl/candidates/sklearn_regression.py`
- `tests/contract/automl/test_sklearn_regression.py`
- `tests/e2e/test_regression.py`
- `examples/regression/workflow.yaml`
- `src/gmldf/automl/default_spaces.py`

**Estimated scope:** Medium (5 files).

<a id="t051"></a>

### [ ] T051: Implement explicit clustering assessment

**Description:** Provide task-appropriate first-release clustering evaluation without a supervised-metric assumption.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] Require explicit clustering task/candidates/metric and a valid internal or external-label assessment protocol.
- [ ] Reject degenerate cluster counts, insufficient data, invalid/non-finite scores, and supervised-only metrics without labels.
- [ ] Clustering evidence describes its assessment limits without pretending it has forecasting/classification accuracy.

**Verification:**

```sh
python3 -m pytest tests/unit/automl/test_clustering_protocol.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Record supported candidate/assessment limitations; users explicitly configure the task, algorithm list, and valid metric.

**Dependencies:** T038, T017

**Files likely touched:**

- `src/gmldf/automl/clustering.py`
- `tests/unit/automl/test_clustering_protocol.py`
- `SPEC-automl.md`

**Estimated scope:** Medium (3 files).

### Checkpoint C18: After T049, T050, T051

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 19: T052, T053, T054

<a id="t052"></a>

### [ ] T052: Fit a clustering candidate

**Description:** Deliver this automl capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] The explicitly configured clustering estimator uses shared budgets/failures and returns cluster assignments plus assessment evidence. Its default search domains are registered and overridable.
- [ ] A generic clustering end-to-end example preserves row identity and preprocessing across save/load and supported prediction.
- [ ] Predict-unsupported algorithms declare that limitation before an inference run.

**Verification:**

```sh
python3 -m pytest tests/contract/automl/test_clustering.py tests/e2e/test_clustering.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T051, T047, T086

**Files likely touched:**

- `src/gmldf/automl/candidates/sklearn_clustering.py`
- `tests/contract/automl/test_clustering.py`
- `tests/e2e/test_clustering.py`
- `examples/clustering/workflow.yaml`
- `src/gmldf/automl/default_spaces.py`

**Estimated scope:** Medium (5 files).

<a id="t053"></a>

### [ ] T053: Add XGBoost candidates

**Description:** Deliver this automl capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] Explicitly supported classification/regression variants validate parameters and reuse task-specific evaluation. Its default search domains are registered and overridable.
- [ ] CPU example fits obey budgets/cancellation and serialize/reload without preprocessing drift.
- [ ] Spark-distributed/GPU variants remain unsupported until separately verified; optional dependency isolation holds.

**Verification:**

```sh
python3 -m pytest tests/contract/automl/test_xgboost.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T050, T047, T086

**Files likely touched:**

- `src/gmldf/automl/candidates/xgboost.py`
- `tests/contract/automl/test_xgboost.py`
- `pyproject.toml`
- `src/gmldf/automl/default_spaces.py`

**Estimated scope:** Medium (4 files).

<a id="t054"></a>

### [ ] T054: Add Prophet forecasting

**Description:** Deliver this automl capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] Prophet forecasts from the declared origin/horizon using validated parameters and explicit date/target mapping. Its default search domains are registered and overridable.
- [ ] Validation/test isolation, cancellation, failed fits, and reload predictions pass the shared forecasting contract.
- [ ] Unsupported seasonality/exogenous/grouped settings fail rather than being ignored.

**Verification:**

```sh
python3 -m pytest tests/contract/automl/test_prophet.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T019, T022, T086

**Files likely touched:**

- `src/gmldf/automl/candidates/prophet.py`
- `tests/contract/automl/test_prophet.py`
- `pyproject.toml`
- `src/gmldf/automl/default_spaces.py`

**Estimated scope:** Medium (4 files).

### Checkpoint C19: After T052, T053, T054

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 20: T055, T056, T057

<a id="t055"></a>

### [ ] T055: Add PySpark ML candidates

**Description:** Expand the candidate list only when needed; no adapter stubs for untested models.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] One approved classifier and regressor fit through native Spark pipelines without driver dataframe collection. Its default search domains are registered and overridable.
- [ ] Real Spark tests verify split/preprocessing isolation, metric direction, artifact reload, and resource/cancellation semantics.
- [ ] Record only tested Spark/runtime/candidate combinations; unsupported cancellation modes are rejected.

**Verification:**

```sh
python3 -m pytest tests/integration/automl/test_spark_ml.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T044, T050, T047, T086

**Files likely touched:**

- `src/gmldf/automl/candidates/spark_ml.py`
- `tests/integration/automl/test_spark_ml.py`
- `docs/compatibility.md`
- `src/gmldf/automl/default_spaces.py`

**Estimated scope:** Medium (4 files).

<a id="t056"></a>

### [ ] T056: Support group-aware and temporal CV

**Description:** Deliver this automl capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-automl.md](../SPEC-automl.md)

**Acceptance criteria:**

- [ ] Group-aware and temporal protocols prevent entity/time leakage with explicit gap/cutoff semantics.
- [ ] Preprocessing is fitted per fold; fold scores, total candidate trials, fold fits, and final refits are accounted separately.
- [ ] Test data never enters folds or tuning; invalid groups/time/fold cardinalities fail early.

**Verification:**

```sh
python3 -m pytest tests/contract/automl/test_group_time_cv.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T048, T050

**Files likely touched:**

- `src/gmldf/automl/splits.py`
- `src/gmldf/automl/search.py`
- `tests/contract/automl/test_group_time_cv.py`
- `docs/evaluation.md`

**Estimated scope:** Medium (4 files).

<a id="t057"></a>

### [ ] T057: Track model comparisons in MLflow

**Description:** Deliver this model-lifecycle capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-model-lifecycle.md](../SPEC-model-lifecycle.md)

**Acceptance criteria:**

- [ ] A real isolated tracking server receives parent/trial runs, parameters, metric direction, outcomes, and artifacts.
- [ ] Required tracking outage fails the run; explicitly best-effort tracking records degraded status.
- [ ] The example/base install still needs no MLflow server or import; credentials stay redacted.

**Verification:**

```sh
python3 -m pytest tests/integration/model_lifecycle/test_mlflow_tracking.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T026, T024

**Files likely touched:**

- `src/gmldf/model_lifecycle/mlflow_tracking.py`
- `tests/integration/model_lifecycle/test_mlflow_tracking.py`
- `pyproject.toml`

**Estimated scope:** Medium (3 files).

### Checkpoint C20: After T055, T056, T057

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 21: T058, T059, T060

<a id="t058"></a>

### [ ] T058: Pin registry aliases to immutable models

**Description:** Deliver this model-lifecycle capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-model-lifecycle.md](../SPEC-model-lifecycle.md)

**Acceptance criteria:**

- [ ] Configured aliases resolve once at run start to immutable versions recorded in provenance.
- [ ] Concurrent alias changes do not change an in-progress inference model; corrupt/missing/untrusted versions fail safely.
- [ ] Registration is explicit and cannot automatically promote a champion or deploy a service.

**Verification:**

```sh
python3 -m pytest tests/integration/model_lifecycle/test_mlflow_registry.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T057, T023

**Files likely touched:**

- `src/gmldf/model_lifecycle/mlflow_registry.py`
- `tests/integration/model_lifecycle/test_mlflow_registry.py`
- `docs/model-registry.md`

**Estimated scope:** Medium (3 files).

<a id="t059"></a>

### [ ] T059: Define object-store transfer semantics

**Description:** Deliver this data-io capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] Object sources/sinks separate format from storage provider and preserve schema/content identity/version where available.
- [ ] Limits, staging/publish semantics, credential resolution, partial failures, and retry safety are explicit.
- [ ] Shared contract cases cover stale versions, missing objects, denied access, interrupted uploads, and changed-content retries.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_object_store.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T013, T006

**Files likely touched:**

- `src/gmldf/data_io/object_store.py`
- `tests/contract/data_io/test_object_store.py`
- `docs/connectors/object-storage.md`

**Estimated scope:** Medium (3 files).

<a id="t060"></a>

### [ ] T060: Read and publish S3 datasets

**Description:** Use provider identity/secret references; do not claim atomic rename or exactly-once behavior absent a provider guarantee.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] CSV/Parquet S3 access uses the shared source/sink contract with explicit identity/version and bounded materialization.
- [ ] Default writes preserve existing destinations; overwrite/append capabilities and non-atomic/ambiguous failures are accurately declared.
- [ ] An isolated live round trip and auth/version/failure cases pass before the exact provider/engine profile is verified.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_s3.py -q
python3 -m pytest tests/integration/data_io/test_s3.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Environment gate: requires approved test credentials/storage; contract tests alone do not complete this task.

**Dependencies:** T059, T013

**Files likely touched:**

- `src/gmldf/data_io/s3.py`
- `tests/contract/data_io/test_s3.py`
- `tests/integration/data_io/test_s3.py`
- `pyproject.toml`

**Estimated scope:** Medium (4 files).

### Checkpoint C21: After T058, T059, T060

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 22: T061, T062, T063

<a id="t061"></a>

### [ ] T061: Read and publish ADLS datasets

**Description:** Use provider identity/secret references; do not claim atomic rename or exactly-once behavior absent a provider guarantee.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] CSV/Parquet ADLS access uses the shared source/sink contract with explicit identity/version and bounded materialization.
- [ ] Default writes preserve existing destinations; overwrite/append capabilities and non-atomic/ambiguous failures are accurately declared.
- [ ] An isolated live round trip and auth/version/failure cases pass before the exact provider/engine profile is verified.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_adls.py -q
python3 -m pytest tests/integration/data_io/test_adls.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Environment gate: requires approved test credentials/storage; contract tests alone do not complete this task.

**Dependencies:** T059, T013

**Files likely touched:**

- `src/gmldf/data_io/adls.py`
- `tests/contract/data_io/test_adls.py`
- `tests/integration/data_io/test_adls.py`
- `pyproject.toml`

**Estimated scope:** Medium (4 files).

<a id="t062"></a>

### [ ] T062: Read and publish Google Cloud Storage datasets

**Description:** Use provider identity/secret references; do not claim atomic rename or exactly-once behavior absent a provider guarantee.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] CSV/Parquet Google Cloud Storage access uses the shared source/sink contract with explicit identity/version and bounded materialization.
- [ ] Default writes preserve existing destinations; overwrite/append capabilities and non-atomic/ambiguous failures are accurately declared.
- [ ] An isolated live round trip and auth/version/failure cases pass before the exact provider/engine profile is verified.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_gcs.py -q
python3 -m pytest tests/integration/data_io/test_gcs.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Environment gate: requires approved test credentials/storage; contract tests alone do not complete this task.

**Dependencies:** T059, T013

**Files likely touched:**

- `src/gmldf/data_io/gcs.py`
- `tests/contract/data_io/test_gcs.py`
- `tests/integration/data_io/test_gcs.py`
- `pyproject.toml`

**Estimated scope:** Medium (4 files).

<a id="t063"></a>

### [ ] T063: Define transactional database I/O contracts

**Description:** Deliver this data-io capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] SQL value parameters and driver-specific validated/quoted identifiers are distinct from arbitrary executable config.
- [ ] Transactions, snapshot limits, append/overwrite/upsert capabilities, and commit/retry receipts are explicit.
- [ ] Unknown commit results or reused write keys with changed payload cannot cause a blind repeated append.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_sql_contract.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T013, T006

**Files likely touched:**

- `src/gmldf/data_io/sql.py`
- `tests/contract/data_io/test_sql_contract.py`
- `docs/connectors/sql.md`

**Estimated scope:** Medium (3 files).

### Checkpoint C22: After T061, T062, T063

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 23: T064, T065, T066

<a id="t064"></a>

### [ ] T064: Read SQL Server tables and queries

**Description:** Confirm target database versions and driver requirements before choosing compatibility pins.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] An approved SQL Server version/driver/auth profile reads typed tables or parameterized queries with encrypted transport.
- [ ] Identifiers/parameters, empty results, Unicode/decimal/timestamps, row/byte bounds, and auth/schema errors pass contract cases.
- [ ] Live evidence records snapshot guarantees or reproducibility limits without credentials.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_sqlserver_read.py -q
python3 -m pytest tests/integration/data_io/test_sqlserver_read.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Environment gate: approved isolated database and credentials; no schema migration in a shared database.

**Dependencies:** T063

**Files likely touched:**

- `src/gmldf/data_io/sqlserver.py`
- `tests/contract/data_io/test_sqlserver_read.py`
- `tests/integration/data_io/test_sqlserver_read.py`
- `pyproject.toml`

**Estimated scope:** Medium (4 files).

<a id="t065"></a>

### [ ] T065: Write SQL Server results safely

**Description:** Only implement modes requested for the confirmed provider; no generic upsert syntax is assumed.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] Default nonreplacement and explicit supported write modes preserve schema and destination boundaries.
- [ ] Transaction rollback, ambiguous commit, duplicate write identity, and changed payload return truthful receipts without unsafe retries.
- [ ] Real isolated database tests verify advertised append/overwrite/upsert modes; unsupported modes reject during preflight.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_sqlserver_write.py -q
python3 -m pytest tests/integration/data_io/test_sqlserver_write.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Environment gate: destructive cases restricted to explicitly isolated test tables.

**Dependencies:** T064, T063

**Files likely touched:**

- `src/gmldf/data_io/sqlserver.py`
- `tests/contract/data_io/test_sqlserver_write.py`
- `tests/integration/data_io/test_sqlserver_write.py`

**Estimated scope:** Medium (3 files).

<a id="t066"></a>

### [ ] T066: Read Oracle tables and queries

**Description:** Confirm target database versions and driver requirements before choosing compatibility pins.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] An approved Oracle version/driver/auth profile reads typed tables or parameterized queries with encrypted transport.
- [ ] Identifiers/parameters, empty results, Unicode/decimal/timestamps, row/byte bounds, and auth/schema errors pass contract cases.
- [ ] Live evidence records snapshot guarantees or reproducibility limits without credentials.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_oracle_read.py -q
python3 -m pytest tests/integration/data_io/test_oracle_read.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Environment gate: approved isolated database and credentials; no schema migration in a shared database.

**Dependencies:** T063

**Files likely touched:**

- `src/gmldf/data_io/oracle.py`
- `tests/contract/data_io/test_oracle_read.py`
- `tests/integration/data_io/test_oracle_read.py`
- `pyproject.toml`

**Estimated scope:** Medium (4 files).

### Checkpoint C23: After T064, T065, T066

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 24: T067, T068, T069

<a id="t067"></a>

### [ ] T067: Write Oracle results safely

**Description:** Only implement modes requested for the confirmed provider; no generic upsert syntax is assumed.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] Default nonreplacement and explicit supported write modes preserve schema and destination boundaries.
- [ ] Transaction rollback, ambiguous commit, duplicate write identity, and changed payload return truthful receipts without unsafe retries.
- [ ] Real isolated database tests verify advertised append/overwrite/upsert modes; unsupported modes reject during preflight.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_oracle_write.py -q
python3 -m pytest tests/integration/data_io/test_oracle_write.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Environment gate: destructive cases restricted to explicitly isolated test tables.

**Dependencies:** T066, T063

**Files likely touched:**

- `src/gmldf/data_io/oracle.py`
- `tests/contract/data_io/test_oracle_write.py`
- `tests/integration/data_io/test_oracle_write.py`

**Estimated scope:** Medium (3 files).

<a id="t068"></a>

### [ ] T068: Read and write Databricks catalog tables

**Description:** Connector support does not establish Databricks runtime/container support.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] Approved catalog/table access uses explicit connection/identity and runtime context rather than notebook globals.
- [ ] Native Spark table paths and any approved external access path are distinguished; no silent driver extraction.
- [ ] Read/write schema, permissions, snapshot provenance, write receipts, and incomplete commits pass real account tests before verification.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_databricks.py -q
python3 -m pytest tests/integration/data_io/test_databricks.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Environment gate: confirmed workspace/runtime and isolated test catalog.

**Dependencies:** T044, T063, T002

**Files likely touched:**

- `src/gmldf/data_io/databricks.py`
- `tests/contract/data_io/test_databricks.py`
- `tests/integration/data_io/test_databricks.py`
- `docs/connectors/databricks.md`

**Estimated scope:** Medium (4 files).

<a id="t069"></a>

### [ ] T069: Read bounded Snowflake datasets

**Description:** Connecting to data externally is not evidence that work executed in a warehouse.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] Approved connector/account/auth profile reads validated tables or parameterized queries with explicit result bounds.
- [ ] Source version/snapshot limitations, type fidelity, permission failures, and materialization are recorded.
- [ ] Real account tests exercise schema/Unicode/decimal/timestamp/empty-result cases; no native execution claim follows from reading.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_snowflake_read.py -q
python3 -m pytest tests/integration/data_io/test_snowflake_read.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Environment gate: isolated Snowflake test data and approved compute/credentials.

**Dependencies:** T063, T002

**Files likely touched:**

- `src/gmldf/data_io/snowflake.py`
- `tests/contract/data_io/test_snowflake_read.py`
- `tests/integration/data_io/test_snowflake_read.py`
- `pyproject.toml`

**Estimated scope:** Medium (4 files).

### Checkpoint C24: After T067, T068, T069

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 25: T070, T071, T072

<a id="t070"></a>

### [ ] T070: Write Snowflake result tables

**Description:** Only scoped test tables may be mutated.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] Supported table-write modes validate identifiers/schema and return transaction/commit/retry receipts.
- [ ] Default existing-table protection, explicit overwrite/upsert keys, and partial/ambiguous commits pass real tests.
- [ ] Replay behavior cannot duplicate an append after uncertain success; unsupported modes reject before mutation.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_snowflake_write.py -q
python3 -m pytest tests/integration/data_io/test_snowflake_write.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Environment gate: approved isolated destination and warehouse usage.

**Dependencies:** T069, T063

**Files likely touched:**

- `src/gmldf/data_io/snowflake.py`
- `tests/contract/data_io/test_snowflake_write.py`
- `tests/integration/data_io/test_snowflake_write.py`

**Estimated scope:** Medium (3 files).

<a id="t071"></a>

### [ ] T071: Read and publish Delta tables

**Description:** Deliver this data-io capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] Delta reads record table version/schema and supported writes return a commit/version receipt.
- [ ] Default protection plus explicit append/overwrite pass real pinned Spark/Delta tests.
- [ ] Non-Delta engines reject Delta output unless a separately verified compatible provider exists.

**Verification:**

```sh
python3 -m pytest tests/integration/data_io/test_delta_batch.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T044, T009

**Files likely touched:**

- `src/gmldf/data_io/delta.py`
- `tests/integration/data_io/test_delta_batch.py`
- `pyproject.toml`
- `requirements/spark.txt`

**Estimated scope:** Medium (4 files).

<a id="t072"></a>

### [ ] T072: Merge Delta results with declared keys

**Description:** Deliver this data-io capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] Upsert requires valid keys and an explicit duplicate-key policy; null/duplicate cases are tested.
- [ ] Repeated logical writes and changed-payload replays obey the declared transaction/idempotency contract.
- [ ] Injected merge failures expose commit state without claiming cross-table atomicity or streaming support.

**Verification:**

```sh
python3 -m pytest tests/integration/data_io/test_delta_upsert.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T071, T063

**Files likely touched:**

- `src/gmldf/data_io/delta.py`
- `tests/integration/data_io/test_delta_upsert.py`
- `docs/connectors/delta.md`

**Estimated scope:** Medium (3 files).

### Checkpoint C25: After T070, T071, T072

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 26: T073, T074, T075

<a id="t073"></a>

### [ ] T073: Install the library in a Databricks host

**Description:** Document and verify installing compatible extras into an existing supported Databricks Python environment; no job orchestration adapter.

**Spec:** [SPEC-execution.md](../SPEC-execution.md)

**Acceptance criteria:**

- [ ] The library and selected extras install in a recorded compatible Databricks runtime/environment.
- [ ] An existing Spark/session context is passed explicitly; imports use no notebook-only globals.
- [ ] Base/optional import behavior and safe missing/incompatible-backend errors are demonstrated without job-management calls.

**Verification:**

```sh
python3 -m pytest tests/integration/execution/test_databricks_install.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Requires an existing authorized Databricks host; no job creation or custom-container publishing is included.

**Dependencies:** T030, T068, T002

**Files likely touched:**

- `examples/environments/databricks/install.py`
- `tests/integration/execution/test_databricks_install.py`
- `docs/evidence/databricks-install.md`

**Estimated scope:** Medium (3 files).

<a id="t074"></a>

### [ ] T074: Verify current-host Databricks execution

**Description:** Call Python/CLI inside the existing host and verify library compatibility, not platform launch control.

**Spec:** [SPEC-execution.md](../SPEC-execution.md)

**Acceptance criteria:**

- [ ] Data-only and a compatible explicitly configured ML example execute through the normal public API in the existing Databricks host.
- [ ] Output/artifact/provenance/session ownership behavior passes real host checks.
- [ ] Unsupported engine/model/compute combinations reject explicitly; the library issues no remote submit/status/cancel requests.

**Verification:**

```sh
python3 -m pytest tests/integration/execution/test_databricks_invocation.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** An existing authorized runtime is required; test evidence covers only the actual host profile.

**Dependencies:** T073, T055

**Files likely touched:**

- `examples/environments/databricks/run.py`
- `tests/integration/execution/test_databricks_invocation.py`
- `docs/evidence/databricks-invocation.md`

**Estimated scope:** Medium (3 files).

<a id="t075"></a>

### [ ] T075: Invoke the library inside a Snowflake-supported host

**Description:** Users install/invoke compatible optional dependencies in their own supported Snowflake Python/container environment.

**Spec:** [SPEC-execution.md](../SPEC-execution.md)

**Acceptance criteria:**

- [ ] Installation and public API execution succeed inside a documented existing Snowflake-supported host profile.
- [ ] Configured connector/engine/model behavior and durable artifacts use the supplied identity/context without hidden extraction.
- [ ] The library creates no compute pool/image repository/job/service and performs no remote lifecycle management.

**Verification:**

```sh
python3 -m pytest tests/integration/execution/test_snowflake_invocation.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Requires an existing authorized compatible host; users/platforms own setup and launch.

**Dependencies:** T030, T070, T002

**Files likely touched:**

- `examples/environments/snowflake/run.py`
- `tests/integration/execution/test_snowflake_invocation.py`
- `docs/evidence/snowflake-invocation.md`

**Estimated scope:** Medium (3 files).

### Checkpoint C26: After T073, T074, T075

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 27: T076, T077, T078

<a id="t076"></a>

### [ ] T076: Guard Snowflake host capability boundaries

**Description:** Verify supported combinations and clear rejections; do not invent a new processing engine or in-warehouse orchestration mode.

**Spec:** [SPEC-execution.md](../SPEC-execution.md)

**Acceptance criteria:**

- [ ] Support evidence distinguishes reading Snowflake data externally from execution inside a particular supported Snowflake host.
- [ ] Requests for incompatible Spark/pandas/Polars/DuckDB/model combinations reject rather than silently moving data or changing engine.
- [ ] Record dependencies, enforced transfer limits, and session ownership; do not promise all engines can run inside a warehouse.

**Verification:**

```sh
python3 -m pytest tests/contract/execution/test_snowflake_capabilities.py -q
python3 -m pytest tests/integration/execution/test_snowflake_capabilities.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Real host evidence is required for claimed combinations; no new native-engine contract is assumed.

**Dependencies:** T075, T002

**Files likely touched:**

- `tests/contract/execution/test_snowflake_capabilities.py`
- `tests/integration/execution/test_snowflake_capabilities.py`
- `docs/compatibility.md`

**Estimated scope:** Medium (3 files).

<a id="t077"></a>

### [ ] T077: Verify user-managed AWS-hosted invocation

**Description:** Exercise the same library API in an existing AWS-hosted Python/container environment; no EKS/ECS/Batch/SageMaker control-plane adapter.

**Spec:** [SPEC-execution.md](../SPEC-execution.md)

**Acceptance criteria:**

- [ ] An existing user-managed AWS host installs compatible extras and runs configured data/ML paths through Python or CLI.
- [ ] Host identity and S3 artifacts work without embedded credentials; outputs persist and runtime identity is recorded.
- [ ] The library makes no infrastructure/job-management requests, and evidence identifies only the tested host/profile.

**Verification:**

```sh
python3 -m pytest tests/integration/execution/test_aws_host.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** An existing authorized AWS test host is needed; no new orchestration target or cluster is selected.

**Dependencies:** T030, T060, T002

**Files likely touched:**

- `examples/environments/aws/run.py`
- `tests/integration/execution/test_aws_host.py`
- `docs/evidence/aws-host.md`

**Estimated scope:** Medium (3 files).

<a id="t078"></a>

### [ ] T078: Verify source provenance and commit recovery

**Description:** Deliver this data-io capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-data-io.md](../SPEC-data-io.md)

**Acceptance criteria:**

- [ ] Documented source snapshots/versions are reflected in RunResult; unknown guarantees explicitly limit reproducibility.
- [ ] An advertised idempotent write survives repeated requests and rejects changed-payload identity reuse under injected ambiguous commit.
- [ ] Providers lacking those guarantees explicitly disable retries; no matrix entry gains stronger guarantees than live evidence.

**Verification:**

```sh
python3 -m pytest tests/contract/data_io/test_provenance.py -q
python3 -m pytest tests/integration/data_io/test_commit_recovery.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T062, T065, T067, T068, T070, T072

**Files likely touched:**

- `tests/contract/data_io/test_provenance.py`
- `tests/integration/data_io/test_commit_recovery.py`
- `docs/evidence/io-guarantees.md`

**Estimated scope:** Medium (3 files).

### Checkpoint C27: After T076, T077, T078

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 28: T079, T080, T081

<a id="t079"></a>

### [ ] T079: Demonstrate enterprise policy templates

**Description:** Deliver this core-contracts capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-core-contracts.md](../SPEC-core-contracts.md)

**Acceptance criteria:**

- [ ] Approved operation/connector/output/runtime restrictions deny work before data access and produce redacted audit evidence.
- [ ] A reusable config template works with environment-specific connections without customer code copies.
- [ ] Documentation distinguishes these local hooks from IAM, tenancy, SSO, or a hosted governance product.

**Verification:**

```sh
python3 -m pytest tests/e2e/test_enterprise_policy.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T026, T058

**Files likely touched:**

- `examples/enterprise/policy.yaml`
- `examples/enterprise/workflow.yaml`
- `tests/e2e/test_enterprise_policy.py`
- `docs/enterprise.md`

**Estimated scope:** Medium (4 files).

<a id="t080"></a>

### [ ] T080: Optionally assess a user's business dataset (optional)

**Description:** Supplement generic release acceptance with an explicitly supplied business dataset. This optional task is not a single-use-case release gate.

**Spec:** [SPEC-recipes.md](../SPEC-recipes.md)

**Acceptance criteria:**

- [ ] Record the approved dataset access/snapshot, quality metric/threshold, horizon, and resource budget before running.
- [ ] Evaluate user-listed candidates (including a baseline only if listed) with the declared untouched assessment protocol and report whether the user's actual threshold was met.
- [ ] No threshold is weakened to pass; customer data/credentials are never committed.

**Verification:**

```sh
python3 -m pytest tests/e2e/test_business_acceptance.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Gate:** Optional: requires a user's dataset access, declared metric/quality threshold, and authorized resource scope; absence does not narrow or block generic release acceptance.

**Dependencies:** T033

**Files likely touched:**

- `examples/forecasting/business-acceptance.yaml`
- `tests/e2e/test_business_acceptance.py`
- `docs/evidence/business-acceptance.md`

**Estimated scope:** Medium (3 files).

<a id="t081"></a>

### [ ] T081: Audit the full first-release capability inventory

**Description:** Require all named connectors/engines/tasks/model integrations and output types, each in a verified supported combination.

**Spec:** [SPEC-recipes.md](../SPEC-recipes.md)

**Acceptance criteria:**

- [ ] Every originally requested connector, four engines, four task families, named ML integrations, and output type has implementation and verified acceptance evidence before release completion.
- [ ] Each claimed combination links actual host/provider/version evidence; unsupported pairs are explicit and cannot hide an entirely missing required capability.
- [ ] Import isolation, bounds, security failures, persistence, and task-specific evaluation requirements have no unexplained spec gaps.

**Verification:**

```sh
python3 -m pytest tests/contract/core/test_capability_evidence.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T045, T052, T053, T054, T055, T056, T058, T078, T074, T076, T077, T079, T085, T086, T087, T048, T050, T052

**Files likely touched:**

- `docs/compatibility.md`
- `docs/evidence/capability-acceptance.md`
- `tests/contract/core/test_capability_evidence.py`

**Estimated scope:** Medium (3 files).

### Checkpoint C28: After T079, T080, T081

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.


## Stage 29: T082, T083, T084

<a id="t082"></a>

### [ ] T082: Verify optional environment installations

**Description:** Deliver this execution capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-execution.md](../SPEC-execution.md)

**Acceptance criteria:**

- [ ] Each claimed environment installs from its pinned resolution independently; dependencies for incompatible backends need not coexist.
- [ ] Base/data-only imports avoid unnecessary ML/cloud libraries and missing extras produce useful errors.
- [ ] Environment/version/architecture identities match capability evidence; untested profiles cannot become verified.

**Verification:**

```sh
python3 -m pytest tests/integration/execution/test_install_profiles.py -m integration -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T081

**Files likely touched:**

- `tests/integration/execution/test_install_profiles.py`
- `requirements/compatibility-index.json`
- `docs/evidence/install-profiles.md`

**Estimated scope:** Medium (3 files).

<a id="t083"></a>

### [ ] T083: Finish user-facing configuration documentation

**Description:** Deliver this recipes capability through the provider contracts, keeping previously completed paths working.

**Spec:** [SPEC-recipes.md](../SPEC-recipes.md)

**Acceptance criteria:**

- [ ] Documented Python/CLI data/train/infer invocations execute in the current host; no remote submit/status/cancel API is advertised.
- [ ] Users can locate examples, input/output schemas, candidate budgets, failure meanings, profiles, and supported combinations.
- [ ] BizInsights is acknowledged as selective inspiration without copying its code, customer logic, or mandatory layer conventions.

**Verification:**

```sh
python3 -m pytest tests/e2e/test_documented_commands.py -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T082

**Files likely touched:**

- `README.md`
- `docs/configuration.md`
- `docs/quickstart.md`
- `docs/compatibility.md`
- `tests/e2e/test_documented_commands.py`

**Estimated scope:** Medium (5 files).

<a id="t084"></a>

### [ ] T084: Review generic first-release acceptance

**Description:** Review the complete requested capability inventory against the confirmed library intent. A forecasting milestone or optional business-data test cannot substitute for generic release readiness.

**Spec:** [SPEC-recipes.md](../SPEC-recipes.md)

**Acceptance criteria:**

- [ ] All eight specs and the confirmed intent trace to completed required capability evidence; each named connector/engine/task/model family has a verified supported combination.
- [ ] Only user-listed algorithms/metric/engine run; default overrides, explicit bounded transfers, evaluated results and optional full-data refit pass end-to-end checks.
- [ ] User review records remaining technical blockers accurately; no package publish, merge, deployment, or remote-job management is performed.

**Verification:**

```sh
python3 -m pytest tests/unit tests/contract tests/e2e -m 'not integration' -q
```

- [ ] Command(s) pass in the selected environment; inspect actual outputs/evidence against the criteria.

**Dependencies:** T083, T033

**Files likely touched:**

- `docs/evidence/final-acceptance.md`
- `tasks/todo.md`
- `tasks/plan.md`

**Estimated scope:** Medium (3 files).

### Checkpoint C29: After T082, T083, T084

- [ ] Required tasks in this group meet their criteria; incomplete live evidence remains visible. Optional work is not counted as a release blocker.
- [ ] Applicable focused/regression tests, build, lint, and formatting pass for implemented environments; no weakening or placeholder support.
- [ ] Review milestone evidence and dependencies before proceeding; intermediate examples do not constitute release completion.
