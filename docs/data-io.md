# Local CSV reader

`gmldf.data_io.csv.PandasCSVReader.read(source, context)` returns a `DatasetRef` with a native pandas dataframe in its process-local `handle`. It requires context capability id `pandas_csv_read`. The current verified profile is CPython 3.11.18/macOS arm64 with the pinned `pandas` extra; importing the reader does not import pandas or NumPy.

Install in your own Python environment:

```sh
python -m pip install -e '.[pandas]'
```

A source uses this schema (workflow execution is a subsequent task):

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

Metadata records engine/schema, actual row count and absolute source URI. Source version remains unknown; mutable local files have limited reproducibility. The reader validates row widths then parses through pandas and materializes the selected local file in memory. Snapshot guarantees, resource limits, workflow execution and other I/O profiles remain separate tasks.

Parsing API reference: [pandas read_csv](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html).
