# Tutorial 1 — Salary vs. operating budget, by department

> **Question.** Which Cambridge departments spent the most on salaries in the FY2027 budget, and
> how does that line up with their operating budget?

This is the tutorial to start with: a clean cross-dataset join between two datasets the portal never
joined for you. It also carries a small but important caveat — that the join worked *here* is not a
guarantee it works *everywhere*.

## The two datasets

| Dataset | id | Key field |
|---|---|---|
| Budget – Salaries | `ixg8-tyau` | `department`, `total_salary` |
| Budget – Operating Expenditures | `5bn4-5wey` | `department_name` |

Discover both by searching the catalog and reading their `columns_field_name` metadata:

```bash
uv run scripts/search_catalog.py "budget salaries"
uv run scripts/search_catalog.py "operating expenditure"
```

Cache them:

```bash
uv run scripts/fetch_dataset.py ixg8-tyau
uv run scripts/fetch_dataset.py 5bn4-5wey
```

## The cross-reference

Open a DuckDB connection over the cache — `ixg8-tyau` becomes the view `ds_ixg8_tyau`,
`5bn4-5wey` becomes `ds_5bn4_5wey`:

```python
from cambridge_data import warehouse

con = warehouse.connect()
con.sql("""
    SELECT s.department                                   AS department,
           COUNT(*)                                       AS positions,
           ROUND(SUM(TRY_CAST(s.total_salary AS DOUBLE))) AS salary
    FROM ds_ixg8_tyau AS s
    GROUP BY 1
    ORDER BY 3 DESC
    LIMIT 3
""")
```

Every Socrata column arrives as a string, so `TRY_CAST(total_salary AS DOUBLE)` recovers the
number. Through the MCP server this is the `query` tool, which returns the result as JSON-native
rows.

## The caveat: a clean join is a per-pair result, not a guarantee

For FY2027 the salary and operating datasets joined on **plain equality** — 15 of ~17 departments
matched, no normalisation needed. That is a happy case. **Do not assume it holds for other dataset
pairs.** Department/agency naming isn't consistently keyed portal-wide; the two `department` fields
happen to agree here, but a future pair may need a mapping table or a fuzzy match before they line
up. Treat "the join was clean" as a finding about *these two datasets in FY2027*, not a property of
the portal.

The defensive habit: after any cross-dataset join, sanity-check the join cardinality (how many rows
on each side matched) and spot-check a couple of unmatched keys. A join that drops 20% of rows
"silently" is usually a naming mismatch, not an absence.

## What this tutorial demonstrates

- Two datasets, one SQL join — the core of the toolkit.
- Reading `columns_field_name` before querying (the trap that bites first).
- `TRY_CAST` for the all-strings column convention.
- The "clean join ≠ guaranteed join" caveat that generalises to every cross-dataset question.

For the full FY2027 analysis (chart, the complete department ranking), see the upstream
`local-data-experiments` repo — it was delivered inline and predates the report-mode convention, so
it isn't in `docs/reports/`.
