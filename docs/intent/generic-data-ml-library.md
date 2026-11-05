# Confirmed Intent: Generic Data and Machine Learning Library

Status: explicitly confirmed by the user on 2026-11-05; saving and document alignment authorized.
This is the product intent. Detailed implementation choices remain proposals until recorded or tested.

## Outcome and Users

Build a generic, pip-installable Python library for enterprise teams and external developers. Users execute it themselves through Python or CLI in their chosen supported environment.

## First Release

The first release is a reusable library, not a sales-forecasting or other use-case-specific product.
It includes all requested ingestion options: CSV, Parquet, S3, SQL Server, Oracle, Databricks, Snowflake, ADLS, and Google Cloud Storage.
It supports config-selected Spark, pandas, Polars, and DuckDB processing.
Classification, regression, forecasting, and clustering are all first-release task families, each with a small supported algorithm set.
Requested ML integrations include scikit-learn, XGBoost, PySpark ML, ARIMA, and Prophet.
Result destinations include files, tables, databases, and Delta; MLflow supports optional tracking/model lifecycle integration.

These requirements do not imply every connector × engine × algorithm × environment combination works.
Document supported combinations and reject unsupported requests explicitly. Each named capability needs real acceptance evidence before first-release completion.

## User-Controlled Configuration

- Explicit processing engine and ML task; no automatic task inference or silent engine switching.
- Explicit algorithm list: evaluate only listed candidates. Do not add installed algorithms or even an unlisted baseline.
- Explicit model-selection metric, appropriate to the chosen task.
- Default hyperparameter search ranges for listed algorithms, with user overrides.
- Bounded tuning and configured output destinations.
- Cross-engine training only through an explicitly enabled, supported transfer with row/byte limits; reject absent or unsafe transfers.

## Model Results

Return the evaluated winning pipeline and evaluation evidence by default.
Offer an explicit config option to refit the selected pipeline on all available training-run data after evaluation.
Preserve the evaluated model and its report, identify the refitted artifact separately, and do not attribute the earlier scores to the refitted model.
A forecast's origin follows the actual fitted artifact's data cutoff; inference does not secretly refit.

## Packaging and Portability

Ship a lightweight base package plus optional dependencies for engines, connectors, and model families.
Users may install and invoke compatible subsets locally, inside containers/Kubernetes, in AWS-hosted environments, Databricks, or Snowflake-supported Python/container environments.
Pip installation is separate from verified execution compatibility; no universal runtime or algorithm compatibility is promised.
The library may accept an existing engine/session/context from its host.

## Out of Scope

Infrastructure provisioning, remote-job submission/status/cancellation management, a scheduler service, and automatic production deployment.
The user or their existing platform owns those responsibilities. In-process deadlines and cancellation of library-owned work remain required.
Examples, synthetic fixtures, and optional user-owned launch manifests demonstrate the library; they do not narrow first-release scope.

## What Remains an Implementation Choice

Package name, supported Python/dependency versions, schema library, tested platform profiles, concrete per-task algorithms/search ranges, and provider-specific authentication/transaction semantics.
Per-dataset business-quality thresholds belong to users, not one mandatory use case for the library release.
