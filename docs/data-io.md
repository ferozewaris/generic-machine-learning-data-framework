# Local CSV reader

`gmldf.data_io.csv.PandasCSVReader.read(source, context)` returns a `DatasetRef` with a native pandas dataframe in its process-local `handle`. It requires context capability id `pandas_csv_read`. The current verified profile is CPython 3.11.18/macOS arm64 with the pinned `pandas` extra; importing the reader does not import pandas or NumPy.

Install in your own Python environment:

```sh
python -m pip install -e '.[pandas]'
```

A CSV source uses this schema:

```yaml
id: raw
connector: csv
location: input.csv
columns:
  name: string
  amount: decimal
  day: date
options:
  encoding: utf-8
  delimiter: ','
  null_values: ['NULL']
  date_formats:
    day: '%Y-%m-%d'
```

Columns are explicit; schema inference is not supported. Supported types: `string`, nullable `int64`/`float64`/`boolean`, exact `decimal`, `date`, `timestamp`. Column names must match the header exactly; header ordering is retained. Duplicate headers, extra/missing fields, malformed quoted records and incompatible types fail. Header-only input is a valid empty dataset; a zero-byte file has no schema header and fails.

Encoding, single-character delimiter and null tokens are required. `decimal` defaults to `.` and can be `,`; boolean tokens are exactly `true` and `false`. Date/timestamp columns require exact-format declarations; implicit empty/`NaT` coercions are rejected unless the value is a declared null token. Dates must be midnight; timestamp `utc: true` explicitly normalizes offsets to UTC. Reserved framing delimiters (newline, carriage return, NUL and double quote) and non-text codecs are rejected. CSV quoting uses standard double quotes.

Only local regular files and local `file:` URIs are accepted. Relative paths are relative to the caller's working directory at this provider boundary; config-relative resolution belongs to execution. The reader rejects remote URLs and does not resolve credentials. Capability/allowlist checks precede data access. Use the complete workflow preflight when composing providers so all policies/capabilities are checked before the first source read.

Errors distinguish invalid parser configuration (`ConfigError`), source access (`DATA_INVALID` at `sources.ID.location`), malformed rows (`.rows`), and schema/cast failures (`.columns`). Export controlled errors with `public_error`; internal causes can contain source paths/data and must not be logged publicly.

Metadata records engine/schema, actual row count and absolute source URI. Source version remains unknown; mutable local files have limited reproducibility. The reader validates row widths then parses through pandas and materializes the selected local file in memory. Snapshot guarantees, resource limits and remote I/O profiles remain separate tasks. See workflow.md for local composition.

Parsing API reference: [pandas read_csv](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html).

## Local CSV writer

`PandasCSVWriter.write(dataset, sink, context)` accepts a native pandas handle and returns a `WriteReceipt`. Context must allow `pandas_csv_write_new` for the default mode or `pandas_csv_write_overwrite` for explicit replacement. The destination's parent directory must exist.

```yaml
id: result
connector: csv
dataset: raw
location: result.csv
options:
  encoding: utf-8
  delimiter: ','
  null_value: 'NULL'
  date_formats:
    day: '%Y-%m-%d'
```

The writer requires encoding, delimiter and a single null token. It renders declared column types, lowercase booleans, decimal separators and explicit temporal formats without changing the input frame. Non-midnight dates, incompatible native values, non-finite numbers and values whose rendered representation equals the null token fail before publication. CSV headers are retained even for zero rows; index values are not exported. Unicode delimiters are supported. Timestamp precision follows the explicitly chosen format.

Staging uses a private temporary directory in the destination filesystem and mode-0600 files. Completed bytes are flushed before a single-file atomic publish: default `error_if_exists` cannot replace an existing or concurrently created destination; `overwrite` explicitly replaces only the selected file. Append and upsert are unsupported. Atomic visibility does not imply directory-entry crash durability or a cross-output transaction.

Receipts record the SHA-256 content commit id and row count after a known commit. Failures raise `WriteFailure` with a receipt: failures before commit are `not_committed`; ambiguous acknowledgements are `unknown`; failure after a known commit retains `committed`. Uncommitted/uncertain receipts do not claim a published row count. Retry safety is never or unknown; no retry is performed. Export the controlled error and preserve the receipt when composing a workflow. Source snapshots, crash/cancellation recovery, and source-version linkage remain separate tasks.

## Local Parquet

Install `.[parquet]` for the pinned pandas profile plus PyArrow26.0.1. `PandasParquetReader` and `PandasParquetWriter` in `gmldf.data_io.parquet` implement the same provider interfaces. The local CLI selects them only for `connector: parquet`; CSV-only installations do not need PyArrow. Missing requested dependencies reject before source access with an installation hint.

```yaml
id: raw
connector: parquet
location: input.parquet
columns:
  record_id: string
  amount: float64
options: {}
```

A sink uses `connector: parquet`, `dataset`, `location`, optional explicit `mode: overwrite`, and empty options. Reads require an explicit schema; unknown options reject. One local regular file is read, without dataset/partition discovery. Supported logical types are the same seven types as CSV, with checked physical Arrow types: string/large-string, int64, float64, boolean, decimal, date and timestamp. Other physical types reject rather than silently converting. Physically null columns can satisfy an explicitly declared nullable logical type.

Pandas missing values are treated as nulls; literal NaN text cannot silently become a null. Native nullable integers retain precision, including values above2^53; finite float/decimal checks run before pandas conversion can mask values. Arrow/pandas index metadata is ignored. Writers emit no index, preserve physical column nullability, enforce declared nonnullable columns, reject fractional integer conversions/nonfinite values/nonmidnight dates, and preserve nanosecond timestamp values with Parquet2.6. A `date` preserves its explicitly represented calendar day; a `timestamp` preserves its instant and Arrow timezone. CSV timestamp precision still follows its configured format.

Writes use Snappy compression and the same local atomic publisher, default no-replacement mode and receipt/failure semantics as CSV. Append/upsert and partitioned datasets are unsupported. The writer retains actual nonnull decimal precision/scale through Arrow inference; an entirely null or empty decimal column has no inferable precision and may have physical Arrow null type. The reader's required logical schema preserves its declared decimal meaning; no original decimal precision is claimed for absent values.

Actual local tests verify all four CSV/Parquet workflow input-output combinations and native Unicode/decimal/UTC/large-integer/empty/null records. Installing Arrow also changes pandas string storage; numeric conversions explicitly reject newly introduced nulls under both string-storage implementations. Snapshot/resource limits, crash recovery and remote hosts remain unverified.

References: [Arrow pandas conversion](https://arrow.apache.org/docs/python/pandas.html), [Parquet writer options](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.write_table.html).
