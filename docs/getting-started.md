# Getting started

This page walks through a single cross-dataset question end-to-end, both ways — with the MCP
server (what an agent does) and with the CLI (what a human does). The two share one library, so
they reach the same answer. The question:

> **Which Cambridge departments spent the most on salaries in the FY2027 budget, and how does that
> line up with their operating budget?**

The answer requires joining two datasets the portal never joined for you:
`Budget - Salaries` (`ixg8-tyau`) and `Budget - Operating Expenditures` (`5bn4-5wey`).

## 0. Get the catalog

The catalog is the searchable index of all 280+ datasets, cached locally so discovery is instant
and offline. Pull it first:

```bash
uv run scripts/refresh_catalog.py
```

Through the MCP server, the same step is the `refresh_catalog` tool, which returns the row count
and the cache path.

## 1. Discover

Search the cache by keyword. This matches name, description, category, and tags:

```bash
uv run scripts/search_catalog.py "budget salaries"
```

The output is each result's **id** (a Socrata four-by-four like `ixg8-tyau`), its name, its
category, its link, and — crucially — its **`columns_field_name`** metadata: the *machine* field
names a query actually accepts. Read that field before writing any query. The catalog also carries a
`columns_name` (human display names, e.g. "Planning Board Special Permit") — **do not query with
those**; the SODA API silently returns zero rows if you do.

Through the MCP server this is the `search_datasets` tool, which returns the same `columns_field_name`
and says so in its description, because that is the trap that bites first.

## 2. Describe

Before pulling data, read the full schema and coverage of a dataset — it tells you the field names,
types, and update cadence without downloading a thing:

```bash
uv run python -c "from cambridge_data.catalog import get; import json; print(json.dumps(get('ixg8-tyau'), indent=2))"
```

Through the MCP server this is the `describe_dataset` tool (with `probe=true` for a coverage
profile). It reports, among other things, whether the dataset is cached locally — so you know
whether a query will hit the Parquet cache or the live SODA API.

## 3. Fetch and query

Pull the two datasets into the Parquet cache, then cross-reference them in SQL. DuckDB reads
Parquet directly, so the cache *is* the warehouse — there is no separate database to keep in sync:

```bash
uv run scripts/fetch_dataset.py ixg8-tyau
uv run scripts/fetch_dataset.py 5bn4-5wey
```

```python
from cambridge_data import warehouse

con = warehouse.connect()
con.sql("""
    SELECT s.department,
           COUNT(*)                                   AS positions,
           ROUND(SUM(TRY_CAST(s.total_salary AS DOUBLE))) AS salary
    FROM ds_ixg8_tyau AS s
    GROUP BY 1
    ORDER BY 3 DESC
    LIMIT 3
""")
```

Each cached dataset becomes a DuckDB view named `ds_<id_with_underscores>` — `ixg8-tyau` becomes
`ds_ixg8_tyau`. Cross-dataset analysis is plain SQL joins from here.

Through the MCP server, `fetch_dataset` caches the dataset and `query` runs the SQL. The `query`
tool round-trips its result through JSON, so you get clean native numbers — not numpy types that
can't cross the MCP boundary.

## 4. Read the answer like a human

The cross-dataset result is only as good as the fields behind it. Before trusting any total, check
that the field is populated across the rows you're aggregating over — a field can be present in the
schema and empty for most of the data (see [gotchas](gotchas.md)). This is the `field_coverage` and
`coverage_audit` tools, which report a field's population percentage and, for date-bounded fields,
the window they actually cover.

For FY2027 the salary and operating datasets are fully populated, so the join is clean — but the
*habit* is what generalises to the dataset that isn't.

## Where to go next

- [concepts.md](concepts.md) — the full discover → fetch → cross-reference → infer workflow and the
  guards that make it trustworthy.
- [tutorials/01-budget-salary-vs-operating.md](tutorials/01-budget-salary-vs-operating.md) — this
  example in full, including the department-name join that worked *and* the caveat that it won't
  always.
- [gotchas.md](gotchas.md) — read this before you trust any number.
