# Reference

The MCP server (`cambridge_data.mcp`, console script `cambridge-open-data-ma-mcp`) exposes **8
tools** and **4 resources**. Each tool delegates to the same library function a CLI calls, so the
server and the CLI never drift. The server holds no state of its own — each call opens a fresh
DuckDB connection over `data/raw/*.parquet`, so it reflects the cache as of the call and honours
the "no separate warehouse to keep in sync" design.

Run it over stdio (the transport opencode and the other harnesses launch it with):

```bash
uv run cambridge-open-data-ma-mcp
# or: uv run python -m cambridge_data.mcp
```

## Tools

### `refresh_catalog`

Refresh the local catalog cache from the live Socrata Discovery API — the full dataset listing
(~280 datasets: id, name, description, fields, tags, update cadence) into `data/catalog.parquet`.
Run first when `search_datasets` reports a missing cache, or when the portal may have new datasets.
Needs no credentials; the app token only lifts the anonymous rate limit.

- **Args:** none
- **Returns:** `{ datasets: int, path: str }` — the count written and the cache path.

### `search_datasets(keyword, limit=20)`

Search the cached catalog by keyword. Matches name, description, category, and tags. Returns each
result's id, name, category, link, `update_frequency`, and — **crucially** — `columns_field_name`,
the *machine* field names a query actually accepts (not `columns_name`, the display names; querying
with a display name silently returns zero rows).

- **Args:** `keyword: str`, `limit: int = 20`
- **Returns:** `{ keyword, count, results[] }` — each result has `id`, `name`, `category`, `link`,
  `update_frequency`, `columns_field_name[]`.

### `describe_dataset(dataset_id, probe=False)`

Full schema and coverage profile for one dataset: the machine field names (query with these, not the
display names), their types, display names, tags, update cadence, and — when cached — the row count
and the dataset's own earliest/latest date (the **era-gap** signal: a zero result for an old date
may mean the dataset predates it, not that nothing happened). Set `probe=true` for
`coverage_flags`: fields that are only partly populated — the recent-window traps to check before
trusting any total or rate.

- **Args:** `dataset_id: str`, `probe: bool = false`
- **Returns:** the dataset profile as a dict.

### `fetch_dataset(dataset_id, where=None, select=None)`

Pull every row of a dataset via the SODA API and cache it as Parquet
(`data/raw/<id>.parquet`), so it can be cross-referenced in SQL. Supports a server-side `$where`
filter and `$select` projection. Re-running overwrites the cache; check `describe_dataset`'s
`cached`/`fetched_at` first to avoid re-pulling time-sensitive data. Large datasets (millions of
rows) take time; prefer a `$where` filter when a subset suffices.

- **Args:** `dataset_id: str`, `where: str | null`, `select: str | null`
- **Returns:** `{ dataset_id, rows: int, path, fetched_at }`.

### `field_coverage(dataset_id, field, date_field=None)`

Probe how **one** field is actually populated across a *cached* dataset — the defence against the
recent-window trap. Reports the populated fraction and, for populated rows, the date range they
span, and states a `warning` when the pattern looks like a recent operational window rather than the
full history (e.g. a "balance" field only filled for the last year). Always run this before
summing or rate-computing over a field. The field must be a *machine* name from
`columns_field_name`; a display name raises an actionable error listing the real fields.

- **Args:** `dataset_id: str` (must be cached), `field: str`, `date_field: str | null = null`
  (auto-detected from the column names when omitted)
- **Returns:** the field-coverage record as a dict, including a `warning` string when applicable.

### `coverage_audit(dataset_id, threshold=99.0, top=10)`

Automated field-population audit: scan **every** field of a *cached* dataset and return the
least-populated first — the automated version of "check field population before trusting a total."
This is how you discover, up front, that a "complete-looking" column is really a recent window. Use
it instead of hand-checking fields one at a time.

- **Args:** `dataset_id: str` (must be cached), `threshold: float = 99.0` (flag fields below this
  percent populated), `top: int = 10`
- **Returns:** `{ dataset_id, count, flags[] }` — each flag is a field-coverage record with a
  `warning`.

### `list_cached_datasets`

List the dataset ids whose rows are cached locally in `data/raw/`. Only cached datasets can be
queried in SQL or audited for coverage; use `fetch_dataset` to pull one that is not yet cached.

- **Args:** none
- **Returns:** `{ cached: string[] }` — the sorted list of cached dataset ids.

### `query(sql, limit=1000)`

Run a DuckDB `SELECT` over the cached datasets, exposed as one SQL view per dataset named
`ds_<id_with_underscores>` (`ixg8-tyau` → `ds_ixg8_tyau`). This is the cross-referencing step:
join/aggregate across `ds_*` views. Every Socrata column is a string — use
`TRY_CAST(col AS DOUBLE)` for numeric work, and expect join keys (e.g. department names) to need
normalisation before they line up.

> [!WARNING]
> `query` runs **arbitrary SQL over local Parquet only**. It is a trusted single-user tool, **not
> sandboxed** — a public multi-tenant deployment would need a boundary. Prefer
> `describe_dataset` + `coverage_audit` first, so you know the fields exist and are fully
> populated.

- **Args:** `sql: str`, `limit: int = 1000`
- **Returns:** `{ columns: string[], row_count: int, rows: object[] }` on success; `{ error: str,
  sql: str }` on failure. Rows are JSON-native (the result is round-tripped through JSON, so
  `int64`/`datetime64`/numpy arrays are coerced to plain types that cross the MCP boundary).

## Resources

opencode reads these natively via `list_mcp_resources` / `read_mcp_resource`. The other harnesses
reach the same content through the equivalent tools (`search_datasets`, `describe_dataset`, and the
report corpus).

### `cambridge://catalog`

The full dataset index for data.cambridgema.gov (~280 datasets), compact: id, name, category,
update frequency, and last-updated per dataset. `application/json`. Read this to discover datasets;
use `describe_dataset(id)` for a single dataset's full schema and coverage.

### `cambridge://datasets/{dataset_id}`

The full schema-and-coverage profile for one dataset: machine field names, types, display names,
tags, update cadence, and (when cached) row count and date range. `application/json`. Read this
before writing a query.

### `cambridge://reports`

The list of finished analysis reports in `docs/reports/`, by slug. `application/json`. The corpus
lives in the *upstream* `local-data-experiments` repo; a fresh public install has none until it
populates its own `docs/reports/`.

### `cambridge://reports/{slug}`

A finished analysis report's Markdown (self-contained, with a Data provenance section).
`text/markdown`. Raises an actionable error listing available slugs when the slug is unknown.

## A typical call sequence

```text
refresh_catalog                 # once, to get/refresh the index
search_datasets("budget salary")        # find the dataset; read columns_field_name
describe_dataset("ixg8-tyau", probe=true)  # full schema + coverage before touching data
fetch_dataset("ixg8-tyau")              # cache it (idempotent)
coverage_audit("ixg8-tyau")             # which fields are partial?
query("SELECT ... FROM ds_ixg8_tyau")   # the cross-reference
```
