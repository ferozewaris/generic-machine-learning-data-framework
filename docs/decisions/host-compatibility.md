# Host compatibility boundaries

Recorded 2026-11-05 for T002. This is a test-profile definition, not live platform evidence.

| Host | Profile to verify | Prerequisites |
|---|---|---|
| Local | CPython 3.11.18, macOS arm64, isolated virtual environment | Local package install and core/dev dependencies |
| Container | Linux CPU image, Python 3.11+, compatible selected extras | User-built image, mounted config and durable output directory |
| Kubernetes | Same tested container identity and selected extras | Existing user-managed cluster/workload, persistent output, user launch |
| AWS-hosted | Existing Python/container host with selected extras | User-managed host/identity, explicit storage/network permissions |
| Databricks | A recorded supported runtime/Python/compute profile | Existing workspace/session, compatible wheel/extras and supplied context |
| Snowflake | A recorded supported Python/container facility | Existing compatible host and identity, approved dependencies and storage |

For every host, record Python, OS/CPU, package/dependency, driver, engine, algorithm, and session identity. Local validation or a successful pip install is not proof of data/ML execution.

Databricks and Snowflake **connectors** describe data access. Running inside their hosts is separate evidence. Neither implies all four processing engines run in every facility; reject unsupported combinations and unsafe transfers.

No AWS orchestrator is selected. The library does not provision infrastructure or submit/poll/cancel platform jobs. Existing sessions remain caller-owned. Networked tests require an already authorized environment and isolated data/output destinations.

Sources consulted: [Databricks library installation](https://docs.databricks.com/aws/en/libraries/) and [Snowpark Python setup](https://docs.snowflake.com/en/developer-guide/snowpark/python/setup). Exact runtime/driver versions remain unverified until integration tasks execute in an actual host.
