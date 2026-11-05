# Spec: Library Installation and Host Execution

Module id: `execution`
Status: Revised to confirmed intent — implementation details remain draft
Depends on: workflow

## Objective

Let users pip-install compatible parts of the generic library and invoke them through Python or CLI in their own supported environment. The library runs inside the user's process/host; users or existing platform tools own job launching.

The [confirmed intent](docs/intent/generic-data-ml-library.md) supersedes remote-job submission/provisioning requirements. Module id `execution` stays stable.

## Tech Stack

Proposed Python package/CLI `gmldf`; exact Python/dependency versions remain compatibility choices.
Minimal base plus optional engine, connector, model-family, and MLflow extras. Extra names below are illustrative until packaging is implemented.
Use an existing Spark session or other host context when supplied; do not depend on notebook globals.
No Kubernetes/Databricks/AWS job-management SDK is required merely to invoke the library.

## Public Boundary

```python
def run(
    config: Mapping[str, object] | str | Path,
    *,
    context: HostContext | None = None,
) -> RunResult:
    """Validate and execute in the caller's current environment."""
```

HostContext supplies an optional existing engine session, credentials resolver, artifact root, and limits/cancellation for this invocation. It does not represent a remote-job client.
Python and CLI share validation, provider resolution, and the workflow implementation.
The lower-level typed workflow API remains available to internal consumers.

## Requirements

- Base installation validates config and reports missing compatible extras without importing every backend.
- Independently installable optional sets cover Spark, pandas, Polars, DuckDB, all requested connectors, scikit-learn, XGBoost, ARIMA, Prophet, and MLflow.
- A supported combination identifies package/Python/driver/engine/model/host versions and actual evidence. Dependency installation alone is insufficient evidence.
- Resolve the processing engine only from config. Do not select it from dataset size, installed libraries, or host branding.
- Attach to a supplied engine session without stopping or reconfiguring host-owned resources unexpectedly. Clean up library-owned resources on completion/failure.
- Python callers and CLI users run data/train/infer in their current environment. The library exposes no submit, remote status, or remote cancellation API.
- Containers and Kubernetes are user-managed hosts. Example images/manifests invoke the same entry point and protect durable outputs/secret mounts; the library does not create jobs or publish images.
- AWS is a hosting/identity/storage compatibility target, not a required choice of EKS/ECS/Batch/SageMaker orchestration API.
- Databricks and Snowflake connectors are distinct from installation/execution inside those platforms. Test each claimed host profile independently using its supported Python/container facilities.
- Snowflake support does not mean every requested engine runs in a warehouse. Declare the actual supported host/engine/task combinations and reject the rest.
- Enforce library-owned trial deadlines and respond to process-level cancellation. Confirm stopped work before reporting cancellation, without claiming control over externally launched jobs.
- User-owned sessions and output destinations retain explicit ownership. Config validation does not contact cloud services; online I/O/tracking uses configured provider permissions.
- No infrastructure provisioning, remote-job lifecycle management, production model deployment, image publishing, or online serving in this module.

## Commands

Proposed after implementation; package name and extras are illustrative:
```sh
python3 -m pip install gmldf
python3 -m pip install 'gmldf[pandas,sklearn,arima]'
python3 -m gmldf validate --config examples/classification/workflow.yaml --profile local --output validation.json
python3 -m gmldf run --config examples/classification/workflow.yaml --profile local --run-id classification-demo --output-dir runs/classification-demo
python3 -m pytest tests/unit/execution tests/contract/execution -q
python3 -m pytest tests/integration/execution -m integration -q
```
No package has been published. T011 implements the local data-only `run` command; see [current CLI behavior](docs/local-execution.md). Other task/backend/host examples remain pending.

## Project Structure

`src/gmldf/execution/`: host-context preparation, public entry point, local invocation and CLI.
`examples/environments/`: optional user-owned container/Kubernetes/platform invocation examples.
`tests/integration/execution/`: installation and host compatibility evidence.
`docs/compatibility.md`: supported combinations.

## Code Style

Use the public boundary above. Keep provider-specific imports lazy and host globals out of public APIs.
Do not wrap platform orchestration SDKs or create a library-owned scheduler.

## Testing Strategy and Success Criteria

1. A base pip install imports/validates without Spark, data engines, MLflow, or cloud drivers; missing requested extras produce useful errors.
2. Python and CLI invoke the same data/train/infer behavior in the current host and return matching results/exit semantics.
3. Config-selected engine/task/algorithms/metric remain unchanged across hosts; unsupported combinations reject before data work.
4. Existing host sessions are reused without unexpected shutdown or mutation; owned resources are cleaned up under failures/cancellation.
5. Local and user-launched container/Kubernetes runs preserve durable output and match supported example results within declared tolerances.
6. Databricks, Snowflake, and AWS-hosted invocation each have real installation/execution evidence for their advertised combinations.
7. Public command/API tests reject remote submit/status/cancel operations and never create platform jobs or provision resources.

## Boundaries

- Always: validate capabilities, document host ownership, isolate optional dependencies, and record actual runtime identity.
- Ask first: change confirmed library responsibilities, publish packages/images, or run paid/destructive host integration checks outside existing authorization.
- Never: provision resources, manage remote jobs, silently switch engines, or advertise universal pip/runtime compatibility.

## Remaining Technical Choices

- Package name, Python range, extras names, environment pins, and host-context injection details.
- Exact tested Databricks/Snowflake Python/container profiles and authentication methods.
- CPU architectures, existing host identities, networking, and artifact-store profiles used for acceptance.
- No AWS orchestration target is needed to define the library.
