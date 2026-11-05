# Core metadata contracts

`gmldf.core.types` contains strict metadata models; serialize with `model_dump_json()` and restore with the concrete model's `model_validate_json()`. Extra fields and opaque compute/model handles are rejected. Compute providers keep those handles separately in process.

- `DatasetRef`: dataset id, engine, ordered column name/type/nullability, materialization kind, optional source URI/version and known row count (`null` means unknown).
- `ArtifactRef`: credential-free URI, immutable version, kind, manifest schema version, SHA-256 checksum and producing run. Integrity does not establish trust; loading must enforce trust separately.
- `TrainingResult`: candidate records, resolved search domains/default versions, metric direction and validation/test scores attributed to `evaluated_model`, feature signature, predictions and fit-data provenance. `model` is the evaluated reference unless a distinct `refit_model` and its own fit-data record are supplied. Evaluation never becomes a score measured on the refitted model.
- `PredictionResult`: the exact model reference and prediction dataset metadata.

URIs in public metadata must be absolute: `file:///...`, `models:/...`, or a scheme with a hostname. They must contain no whitespace, userinfo, query or fragment. Convert local paths with `Path.as_uri()`. Pass credentials through runtime credential references, not URIs. Model parameters, column names, source versions and other metadata must not contain secrets or raw sensitive records.

`gmldf.core.errors.FrameworkError` carries an `ErrorInfo` for public output: an allowlisted code/message, optional bounded field path/stage id, and retry safety (`never`, `safe`, `unknown`). Chain the internal exception with `raise ... from cause` for internal diagnosis. Public reports/logs serialize `error.error`, never internal traceback chains or arbitrary exception strings. Default retry safety is `never`.

These contracts describe metadata, not working I/O, fitting or persistence implementations. No artifact trust or backend compatibility is established by creating a reference.

`RunIdentity` records run/attempt ids, a SHA-256 digest of the redacted config, code version and environment versions. `RunContext` adds a credential-free artifact root, optional UTC deadline and allowed capability ids. Its credential resolver, cancellation predicate and event recorder are process-local callables; JSON and `repr` omit them. Restoring JSON restores metadata only; the caller supplies callbacks in the current process. Empty allowed capabilities authorize no work.

`RunResult` is the run receipt. Pending/running states carry no terminal time/reason; running requires a start time. Terminal states require start/end times and a controlled reason, with no negative durations. Failed runs require safe errors. Successful runs cannot include failed/skipped/cancelled stages or incomplete writes. `StageRecord` and `RunEvent` distinguish failed and skipped work and keep failure/error states consistent. Timestamps require a timezone and normalize to UTC.

`WriteReceipt` records destination, mode, committed/not-committed/unknown outcome, row count when known, optional source version and independent output commit id. An uncertain commit cannot be declared retry-safe. Receipts describe individual outputs, not a cross-output transaction. These types do not implement scheduling, cancellation, retries or persistence; providers and workflow implement those behaviors in subsequent tasks.

`gmldf.core.secrets.Credentials(connection, resolver)` performs no lookup on construction. Providers call `resolve()` only when access is required. Returned `Secret` wrappers hide values in representations; use `reveal()` only at the driver boundary. Resolver failures become `AUTH_FAILED` with an internal cause. Never log resolved driver arguments.

Use `public_error(exception)` for reports and events. Unknown external exceptions become a controlled execution error without stringifying them or traversing causes. `redact()` is a defensive diagnostic copy for known credential values, sensitive mapping keys and credential-bearing URLs; it also replaces opaque/non-finite/cyclic values. It is not permission to log raw data, arbitrary provider exception text or context contents. Public metadata must be constructed from approved fields.
