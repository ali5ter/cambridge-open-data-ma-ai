# Concepts

The toolkit is one library driving three entry points — the CLIs, the MCP server, and ad-hoc
Python — over a small pipeline:

```text
Socrata Discovery API  --refresh_catalog-->  data/catalog.parquet   (searchable dataset index)
Socrata SODA API       --fetch_dataset---->   data/raw/<id>.parquet  (one file per pulled dataset)
data/raw/*.parquet     --warehouse.connect-->  in-memory DuckDB, one view per cached dataset
```

No database server. DuckDB reads Parquet directly, so the Parquet cache is the only state and there
is nothing to keep in sync.

## The workflow: discover → fetch → cross-reference → infer

This is the sequence the Skill drives and the MCP tools expose, one tool per step.

### 1. Discover

Search the local catalog cache first — it is instant and offline, and covers name, description,
category, and tags:

- CLI: `uv run scripts/search_catalog.py "<keyword>"`
- MCP: the `search_datasets` tool

If the cache is missing or looks stale, refresh it (`refresh_catalog.py` / `refresh_catalog`; a
few seconds, ~280 rows). Read the printed `columns_field_name` metadata before fetching — it tells
you field names and types without pulling data. The catalog also exposes
`cambridge://catalog` and `cambridge://datasets/{id}` as MCP resources, so a harness can browse
without a tool call.

### 2. Fetch

Pull a dataset's full contents into the local Parquet cache:

- CLI: `uv run scripts/fetch_dataset.py <dataset-id>`
- MCP: the `fetch_dataset` tool

`fetch_dataset` is idempotent — re-running it overwrites that dataset's cache and records the fetch
in `data/manifest.json`. Large datasets can be pulled with a `$where`/`$select` filter; the smoke
test and the tutorials show both.

### 3. Cross-reference

Open a DuckDB connection with one view per cached dataset, and join in SQL:

- Python: `warehouse.connect()`, then `con.sql(...)`
- MCP: the `query` tool (runs the SQL, returns JSON-native rows)

Views are named `ds_<id_with_underscores>` (`ixg8-tyau` → `ds_ixg8_tyau`). For polygon and point
work, `INSTALL spatial; LOAD spatial;` gives `ST_Area_Spheroid`, `ST_Distance_Spheroid`,
`ST_Centroid`, and `ST_GeomFromGeoJSON` over a dataset's `the_geom` column.

### 4. Infer, and check before you publish

For a straight lookup or aggregate, the cross-reference step is the answer. For anything that hinges
on a single field's value — a payment status, a disposition, a numeric total — or for any novel
cross-dataset inference, **stop and check** before publishing. This is the part that separates a
useful answer from a confident wrong one, and it is where the guards live.

## The guards: why a field's *presence* is not its *population*

A field can exist in the schema and be empty for most of the data. Socrata datasets frequently carry
a field populated for only a recent operational window, or absent for most of a dataset's history.
Computing a rate or total over all rows in that case silently understates or fabricates the answer.

Two probes defend against this. They are the `field_coverage` and `coverage_audit` MCP tools, and
they mirror the two habits in the workflow:

- **`field_coverage(dataset_id, field)`** — probes *one* field: how many rows populate it
  (`count(field) / count(*)`), and for a date-bounded field the `min`/`max` of the window in which
  it is populated. It returns a warning when the populated window is a recent slice of the whole.
- **`coverage_audit(dataset_id)`** — scans *every* field of a cached dataset and returns the least
  populated first: the audit that says "before you trust this dataset, know which fields are
  partial."

Use the same habit at the **dataset** level, not just the field level: a *zero-result* search can
mean "nothing on record" or "wrong dataset era." Check the dataset's own date coverage
(`min`/`max` of its date field) before concluding an absence. `describe_dataset` with `probe=true`
reports this without a full pull.

> [!WARNING]
> The guards are *structural* — they answer "is this field/dataset fully populated?" They do **not**
> encode judgment. Judgment lives in the Skill, not the tools: existence is not delivery; civic
> agreements aren't portal data; a spatial nearest-match is corroboration, not proof. See
> [gotchas](gotchas.md).

## The three portal-wide traps

These recur across every analysis in the tutorials. They are standing entries in the Skill.

1. **Fields populated for only a recent window.** `Cambridge Parking Tickets` (`vnxa-cuyr`, 3.07M
   rows since 2014) has `amount_due` populated for just 146,261 rows (2025 H2), and it means
   *current outstanding balance*, not the original fine. Always check population and date coverage
   before treating a field as authoritative.
2. **Civic agreements are not portal data.** Special permits, leases, dispositions, commitment
   letters, and Council orders exist as PDFs and hearing records, never as structured datasets.
   "What did developer X promise the City" cannot be answered from Socrata at all — the portal
   contributes parcel/ownership corroboration only.
3. **Existence is not delivery.** "The decision contains this condition" is settled by reading the
   document; "it was built / opened / leased / paid" is not. See [gotchas](gotchas.md).

## Output modes

The default is **inline chat plus saved chart PNGs** — the fastest way to see an answer. Choose a
heavier mode when the question calls for it:

- **Report mode** — `docs/reports/<YYYY-MM-DD>-<slug>/report.md`, self-contained (chart copied in,
  not referenced from the gitignored cache), with a **Data provenance** section (dataset ids,
  cached-vs-ad-hoc, exact queries) so the finding is reproducible later. `scripts/report_to_pdf.py`
  renders it to PDF beside the Markdown via headless Chrome.
- **Design-brief handoff** — a structured brief (data summary, key findings, suggested chart types)
  sized for pasting into a design tool, when the user wants a presentation-grade visual.

For genuinely novel cross-dataset inference — as opposed to a straightforward lookup — run that one
reasoning step through the strongest available model. Civic-data claims (budget, crime, housing)
warrant care about confounders and overconfident causal language.
