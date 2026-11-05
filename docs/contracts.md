# Core metadata contracts

`gmldf.core.types` contains strict metadata models; serialize with `model_dump_json()` and restore with the concrete model's `model_validate_json()`. Extra fields and opaque compute/model handles are rejected. Compute providers keep those handles separately in process.

- `DatasetRef`: dataset id, engine, ordered column name/type/nullability, materialization kind, optional source URI/version and known row count (`null` means unknown).
- `ArtifactRef`: credential-free URI, immutable version, kind, manifest schema version, SHA-256 checksum and producing run. Integrity does not establish trust; loading must enforce trust separately.
- `TrainingResult`: candidate records, resolved search domains/default versions, metric direction and validation/test scores attributed to `evaluated_model`, feature signature, predictions and fit-data provenance. `model` is the evaluated reference unless a distinct `refit_model` and its own fit-data record are supplied. Evaluation never becomes a score measured on the refitted model.
- `PredictionResult`: the exact model reference and prediction dataset metadata.

URIs in public metadata must be absolute: `file:///...`, `models:/...`, or a scheme with a hostname. They must contain no whitespace, userinfo, query or fragment. Convert local paths with `Path.as_uri()`. Pass credentials through runtime credential references, not URIs. Model parameters, column names, source versions and other metadata must not contain secrets or raw sensitive records.

`gmldf.core.errors.FrameworkError` carries an `ErrorInfo` for public output: an allowlisted code/message, optional bounded field path/stage id, and retry safety (`never`, `safe`, `unknown`). Chain the internal exception with `raise ... from cause` for internal diagnosis. Public reports/logs serialize `error.error`, never internal traceback chains or arbitrary exception strings. Default retry safety is `never`.

These contracts describe metadata, not working I/O, fitting or persistence implementations. No artifact trust or backend compatibility is established by creating a reference.
