# Tutorial 2 — Are street-cleaning parking tickets paid?

> **Question.** How many tickets issued for parking on the wrong side of the street during street
> cleaning are paid? What's the loss of revenue — tickets paid vs. total issued?

This is the tutorial to read if you want to see the toolkit's *honesty* — the moment it answers
**"not fully answerable from this data"** and shows *why*. It is the canonical example of the
recent-window trap.

## The dataset

`Cambridge Parking Tickets` (`vnxa-cuyr`, 3.07M tickets since 2014). It is large enough that you
query it **live** via the SODA API rather than caching the whole thing:

```python
from cambridge_data import warehouse, client

# live, filtered pull — the SODA API, not the cache
with client.SodaClient() as soda:
    rows = soda.query("vnxa-cuyr",
                      where="amount_due IS NOT NULL AND ticket_issue_date >= '2025-07-01T00:00:00.000'")
```

This is the one step the `cambridge-data` CLI does **not** cover: its `query` subcommand runs
DuckDB over the *cached* `ds_*` views, not live SODA, so a 3M-row dataset is pulled live with
`SodaClient` rather than cached. Every other step here is a `cambridge-data` subcommand.

## Step 1 — check the field before you trust it

The naive path is to `SUM(amount_due)` and call it "revenue lost." Stop. Run the guard first. For a
*cached* dataset that is `cambridge-data audit <id>` (every field, least-populated first) or
`cambridge-data coverage <id> --field <f>` (one field) — the `coverage_audit` and `field_coverage`
tools by another name. Here `vnxa-cuyr` is queried live, not cached, so the same check runs against
the live pull in Python: check population and window:

```sql
-- population: how many rows carry the field at all?
SELECT count(amount_due), count(*) FROM <live: vnxa-cuyr WHERE amount_due IS NOT NULL>

-- window: which dates are populated?
SELECT min(ticket_issue_date), max(ticket_issue_date)
FROM <live: vnxa-cuyr WHERE amount_due IS NOT NULL>
```

The result: `amount_due` is populated for **146,261 of 3.07M rows (4.8%)**, and only for
**2025-07 through 2025-12**. It is a recent operational window, not the full history. And it means
*current outstanding balance*, not the original fine — it reads `$0` for a paid ticket **and** a
voided/dismissed one (indistinguishable from each other), and includes escalated late fees for
unpaid ones. It cannot be summed into a "revenue lost" figure.

## Step 2 — what the data *does* show, in that one window

| | Street cleaning | All violations (context) |
|---|---:|---:|
| Tickets issued | 12,574 | 146,261 |
| `$0` due (paid **or** voided — indistinguishable) | 9,440 (75.1%) | 108,886 (74.4%) |
| Balance still outstanding | 3,134 (24.9%) | 37,375 (25.6%) |
| Outstanding $ (current balance, incl. late fees) | $345,340 | $1,814,710 |

Two findings: street cleaning's 75.1% clearance tracks the citywide 74.4% (not an outlier); and
street cleaning is 8.6% of volume but 19% of the outstanding dollar total — worth a follow-up if
late-fee escalation by violation type ever becomes answerable.

Note the data-quality gotcha that shows up mid-query: `violation_description` is `"STREET CLE"`
(truncated to 10 chars) in the 2025 H2 window but full text `"STREET CLEANING"` in the historical
bulk. Match both when filtering by violation type.

## The honest bottom line

**Not fully answerable from this portal's public data.** No dataset on the portal covers ticket
payments/collections separately (checked: revenue, collections, fine, payment, municipal court,
parking clerk — no matches). A real "tickets paid vs. issued, revenue lost" figure for the full
history would need a records request to Cambridge's Traffic, Parking & Transportation department or
the Parking Clerk's office.

## What this tutorial demonstrates

- The **recent-window trap**: a field present in the schema, populated for 4.8% of rows, meaning
  something other than the column name implies.
- **Check population and window before trusting a total** — the `coverage` / `audit` subcommands
  (`coverage_audit` / `field_coverage` through the server) exist for exactly this.
- **The one Python step.** A 3M-row dataset is pulled live via `SodaClient`; the `cambridge-data`
  CLI's `query` is cache-only, so live SODA stays in Python.
- **An honest "can't answer" is a valid answer.** The toolkit's value includes telling you when the
  data can't carry a claim, and pointing you to where the real data lives.

See the full report (with the chart) in the upstream `local-data-experiments` repo:
`docs/reports/2026-08-05-street-cleaning-ticket-payment-status/`.
