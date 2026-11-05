# Spec: Workflow Composition and Run Coordination

Module id: `workflow`
Status: Revised to confirmed intent — implementation details remain draft
Depends on: data-io, processing, automl, model-lifecycle

## Objective

Execute one validated data-only, training, or inference workflow through the module contracts and report truthful stage and output status.

The [confirmed intent](docs/intent/generic-data-ml-library.md) defines first-release scope; shared conventions are indexed in [CAPABILITY-MAP.md](CAPABILITY-MAP.md).
Implementation status: T010 data-only provider coordination is verified locally; see [workflow behavior](docs/workflow.md). Train/infer, CLI integration, progress, cancellation and recovery remain pending. Requirements below retain the full agreed scope.

## Tech Stack

Python library plus the shared CLI surface. Reuse existing platform schedulers; no scheduler, remote-job management service, queue, or metadata database is part of the first release.
Exact dependency versions and supported runtime profiles remain unresolved until compatibility validation; no new packages are installed by this specification.

## Requirements and Consumer Contracts

```python
def run(
    config: ValidatedWorkflow, context: RunContext, providers: ProviderSet
) -> RunResult: ...
```
ProviderSet supplies declared I/O, processing, AutoML, and lifecycle implementations. Runtime implementations construct context/providers; workflow does not import execution.

- Core validation precedes all work. Runtime preflight checks installed capabilities and policy before source access. Connectivity/permission checks are explicitly online and cannot write business outputs.
- `data`: ingest → stateless transformations → configured dataset outputs; no model dependency/import required.
- `train`: ingest → stateless preparation → explicit bounded transfer if configured → user-listed AutoML with fold-fitted preprocessing → evaluated pipeline and assessment → optional full-data refit → persist distinct artifacts → write model evidence/predictions.
- `infer`: resolve/load immutable pipeline → ingest → configured stateless preparation → validate signature → predict without refitting → outputs.
- Execute ordered steps in dependency order, preserving named dataset lineage. First-release coordination is sequential within one workflow; backend-internal fitting may use declared parallelism. No remote scheduler is required.
- Training config must define which prediction artifact outputs reference. Examples export held-out test predictions from TrainingResult; separate inference config selects an immutable evaluated or refitted model and its actual forecast origin.
- RunResult contains run/attempt id, final status, step/trial outcomes, artifacts, write receipts, and safe errors. Success requires every mandatory stage and output to complete.
- A failed dependency skips downstream consumers. Preserve completed receipts; do not pretend multiple sinks form one transaction.
- Default automatic write retries and resume are disabled. A later retry must use provider-declared idempotency and source/artifact identity. Reusing a completed run id or mismatching its config fails.
- No silent changes to engine, candidate list, source location, split protocol, or tracking policy after preflight.
- Events include stage start/end/failure, durations, candidate progress, output commit status, and cancellation. Logs exclude raw data and credentials by default.
- The current process receives cancellation/deadline through context. Mark cancelled only after library-owned work stops. External job state belongs to the caller/platform; the library does not poll or cancel remote jobs.
- Return the evaluated model by default; when explicitly requested, return the distinct full-data-refitted model while retaining evaluated artifacts/report. No failure may silently substitute a different returned-model policy.

## Commands

Proposed after implementation:
```sh
python3 -m gmldf validate --config examples/data-only/workflow.yaml --profile local --output validation.json
python3 -m gmldf run --config examples/data-only/workflow.yaml --profile local --run-id data-demo --output-dir runs/data-demo
python3 -m pytest tests/unit/workflow tests/contract/workflow -q
```
CLI JSON reports use core contracts; progress goes to stderr. Exit codes: 0 success, 2 config/capability/policy rejection, 1 execution/output failure, 130 confirmed cancellation.

## Project Structure

`src/gmldf/workflow/` owns coordination and provider composition contracts.
`tests/unit/workflow/` uses fake providers; `tests/contract/workflow/` verifies stage ordering and result semantics.
CLI bindings are supplied by execution.

## Code Style

Use the run signature above; isolate orchestration from dataframe/model operations. Prefer a simple ordered execution loop over a custom scheduling framework.

## Testing Strategy and Success Criteria

1. Data-only execution completes without importing AutoML dependencies.
2. Train and infer invoke the expected providers in order; inference makes zero fit calls.
3. Config/capability/policy failures perform no source reads or business writes.
4. Failure injection at every stage prevents dependent work and records completed outputs accurately.
5. One failed mandatory output makes the run failed, with completed and incomplete destinations distinguishable.
6. Run-id reuse/config mismatch is rejected; no blind append retry occurs.
7. CLI and library results agree, and cancellation tests do not report still-running work as cancelled.
8. Config digests, immutable model references, source versions when available, and environment identity are attached to results.
9. End-to-end runs preserve explicit engine/task/candidates/metric, bounded-transfer authorization, default/overridden search ranges, and evaluated-versus-refitted model identity.

## Boundaries

- Always: follow the shared boundaries in the capability map; validate inputs at trust boundaries; retain module-specific failure details without credentials or raw sensitive records.
- Ask first: change the approved provider contracts or scope; run paid or destructive integration checks; publish artifacts or deploy external resources.
- Never: import another module's private implementation, bypass capability checks, or advertise untested support.

## Open Questions

- Which outputs may be explicitly optional, and what degraded-success policy is acceptable?
- Technical choice: source/artifact snapshot and resume support beyond the safe default of no automatic resume. Remote-job management is out of scope, not an open decision.
