# Initial pandas operations

`gmldf.processing.pandas.PandasEngine.transform(dataset, steps, context)` applies a sequence of named single-input operations to a native pandas dataset. It returns a new `DatasetRef` and does not mutate the input frame. This is the initial select/cast/sort slice; other operations, engines, joins and learned preprocessing remain separate tasks.

The verified local environment is the same pinned `pandas` optional profile as the [CSV reader](data-io.md). Context must allow each requested `pandas_select`, `pandas_cast`, or `pandas_sort` capability id. All steps are checked for capability, input names and parameter shapes before any transformation runs. No engine conversion, arbitrary expression, Python import path or algorithm discovery is performed.

```yaml
steps:
  - id: selected
    operation: select
    inputs: [raw]
    params:
      columns: [amount, day]
  - id: typed
    operation: cast
    inputs: [selected]
    params:
      columns:
        amount: float64
        day: timestamp
      date_formats:
        day: '%Y-%m-%d'
  - id: ordered
    operation: sort
    inputs: [typed]
    params:
      by: [day, amount]
      ascending: [true, false]
      nulls: last
```

- `select`: nonempty unique column list; retain that column order and current row order. Unknown columns fail.
- `cast`: nonempty column→type mapping. Initial targets are `string`, nullable `int64`/`float64`, `date`, and `timestamp`. Integer casts reject fractional values and overflow. Numeric casts reject non-finite values. Existing nulls are preserved; invalid values fail instead of coercing to null. Boolean/decimal cast targets are not yet supported; existing values can be selected/sorted.
- Temporal casts require a `date_formats` entry for each temporal target and no unrelated format entries. Parsing uses exact formats. `utc: true` explicitly normalizes timezone offsets to UTC; otherwise native parsed timezone behavior is retained. A `date` target rejects non-midnight time rather than discarding it. Undeclared textual empty/`NaT` values cannot become nulls.
- `sort`: nonempty unique `by` keys, `ascending` boolean or one boolean per key (default true), `nulls: first|last` (default last). Equal keys retain input order. Sorts use native values; lexical text does not become numeric unless explicitly cast first.

Each step's single `inputs` name must equal the current dataset id; the output id becomes the step id. A workflow can later call this boundary per graph node. An empty frame retains the requested schema. Derived references preserve source provenance metadata and update row count/column types; they do not establish a snapshot guarantee.

Unknown operations or mismatched engines reject as unsupported. A missing/non-pandas handle rejects as invalid data. Parameter shape errors are config errors; missing columns, invalid casts or unsupported native comparisons are controlled data errors. Public errors do not contain data values or raw internal exceptions.
