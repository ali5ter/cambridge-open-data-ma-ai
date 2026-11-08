# Tutorial 1 — Salary vs. operating budget, by department

> **Question.** Which Cambridge departments spent the most on salaries in the FY2027 budget, and
> how does that line up with their operating budget?

This is the tutorial to start with: a clean cross-dataset join between two datasets the portal never
joined for you. It also carries a small but important caveat — that the join worked *here* is not a
guarantee it works *everywhere*.

Every step below is a `cambridge-data` subcommand — the cohesive CLI that ships with the toolkit
(`uv sync` installs it; it has one subcommand per MCP tool, so the path a human runs by hand and the
path an agent runs through the server are the same calls over one library). The per-operation
`scripts/*.py` helpers remain as thinner by-hand equivalents of these subcommands.

## The two datasets

| Dataset | id | Key field |
|---|---|---|
| Budget – Salaries | `ixg8-tyau` | `department`, `total_salary` |
| Budget – Operating Expenditures | `5bn4-5wey` | `department_name` |

Discover both, then read each dataset's machine field names — the `columns_field_name` a query
accepts, *not* the display names:

```bash
cambridge-data search "budget salaries"
cambridge-data search "operating expenditure"
cambridge-data describe ixg8-tyau --probe
cambridge-data describe 5bn4-5wey --probe
```

`search` prints each match's id, name, and category; `describe --probe` prints the field table —
display name, the **machine** field name to query with, and its type — plus a coverage read. Query
with the machine column (`department`, `total_salary`, `department_name`), never the display name.

Cache both into `data/raw/` (each `fetch` is idempotent — re-running overwrites that dataset's
Parquet):

```bash
cambridge-data fetch ixg8-tyau
cambridge-data fetch 5bn4-5wey
```

## The cross-reference

Each cached dataset becomes a DuckDB view named `ds_<id_with_underscores>` — `ixg8-tyau` becomes
`ds_ixg8_tyau`. Run the join from the shell:

```bash
cambridge-data query "SELECT s.department AS department,
    COUNT(*) AS positions,
    ROUND(SUM(TRY_CAST(s.total_salary AS DOUBLE))) AS salary
  FROM ds_ixg8_tyau AS s
  GROUP BY 1
  ORDER BY 3 DESC
  LIMIT 3"
```

Every Socrata column arrives as a string, so `TRY_CAST(total_salary AS DOUBLE)` recovers the number.
`query` is the CLI form of the server's `query` tool; append `--json` to pipe the result as
JSON-native rows instead of a table. The same loop an agent runs is
`search_datasets → fetch_dataset → query` — see [tutorial 6](06-drive-the-skill-in-opencode.md).

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

- The `cambridge-data` CLI doing the work — `search` → `describe` → `fetch` → `query`, one
  subcommand per MCP tool.
- Two datasets, one SQL join — the core of the toolkit.
- Reading `columns_field_name` before querying (the trap that bites first).
- `TRY_CAST` for the all-strings column convention.
- The "clean join ≠ guaranteed join" caveat that generalises to every cross-dataset question.

For the full FY2027 analysis (chart, the complete department ranking), see the upstream
`local-data-experiments` repo — it was delivered inline and predates the report-mode convention, so
it isn't in `docs/reports/`.
