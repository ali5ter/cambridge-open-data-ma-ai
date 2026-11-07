# Gotchas

These are the failure modes that turn a plausible-sounding answer into a wrong one. Each is a
standing entry in the Skill and was hit by a real analysis in this repo. Read this before trusting
any number the toolkit returns.

## 1. A field's presence is not its population

A field can be in the schema and empty for most of the data. Socrata datasets often carry a field
populated for only a recent operational window, or absent for most of the history. Computing a
rate or total over all rows in that case silently understates or fabricates the answer.

**The defence:** before trusting a field, check `count(field) / count(*)` and, for a date-bounded
field, the `min`/`max` of the window in which it is populated. The `field_coverage` and
`coverage_audit` tools do exactly this.

> `Cambridge Parking Tickets` (`vnxa-cuyr`, 3.07M rows since 2014) has `amount_due` populated for
> only 146,261 rows (2025-07 through 2025-12, 4.8%) — and it means *current outstanding balance*,
> not the original fine. It reads `$0` for a paid ticket *and* a voided/dismissed one, and includes
> escalated late fees for unpaid ones. It cannot be summed into a "revenue lost" figure.

## 2. Query with the *machine* field name, not the display name

The catalog carries two names per field: `columns_name` (human display, e.g. "Planning Board
Special Permit") and `columns_field_name` (the SODA API field, e.g. `pb_special_permit`). The SODA
API **only** accepts the field name. Querying with a display-derived guess does **not** error — it
silently returns zero rows, which reads as "no match" rather than "wrong field name."

**The defence:** always confirm against `columns_field_name` before writing a `$where`/`$select` or
a join. `search_datasets` and `describe_dataset` surface the field name on purpose.

## 3. A zero-result search can mean "wrong dataset era," not "nothing on record"

Before concluding an absence, check the *dataset's own* date coverage (`min`/`max` of its date
field), not just field population within it.

> `Building Permits: Addition/Alteration` (`qu2z-8suj`) and `Building Permits: New Construction`
> (`9qm7-wbdc`) cover only work issued from **2018-07** onward. Older one- and two-family permits
> live in `Building Permits: 1 and 2 Family - DEPRECATED` (`52p4-36ct`, 2013 through 2018-07),
> which has a *different schema* (`plannumber`/`applicationdate`/`class` vs
> `id`/`issue_date`/`permit_type`) and a compound `Location`-type `address` field that 400-errors
> on `LIKE`/`upper()`. Match on `parcelnumber` instead.

`describe_dataset` with `probe=true` catches this without a full pull.

## 4. Civic agreements are not portal data

Special permits, leases, dispositions, commitment letters, and Council orders exist as PDFs and
hearing records, **never as structured datasets.** "What did developer X promise the City" cannot
be answered from Socrata at all — the portal contributes parcel/ownership corroboration only.

Expect **three separate legal instruments**, and do not conflate them:

- the **Planning Board special permit** (zoning; its conditions may *require* a lease without being
  one);
- a **municipal property disposition** under M.G.L. Ch. 30B + Municipal Code Ch. 2.110 — where the
  money terms live; a two-thirds Council vote, a City Manager Disposition Report, and an RFP; and
- **floor amendments** extracted at the Council vote — binding in practice, but often existing only
  in the hearing record and press coverage, in no filed document.

## 5. Existence is not delivery

"The decision contains this condition" is settled by reading the document. "It was built / opened /
leased / paid" is not — a document or announcement establishes intent as of its own date, and
nobody circles back to report the thing that quietly didn't happen.

**The defence, two moves:**

1. Search bounded to *after* the claimed date — "still vacant," "one year on," the following year's
   coverage.
2. Check the counterparty's *own* website — an organisation that genuinely operates a facility says
   so on its own site.

> **Never let a WebFetch summary carry a status claim.** WebFetch answers via a small fast model
> that reliably flattens future tense into past — "*future* first-floor day care space" and "*will
> open* this fall" both collapse into "opened" under paraphrase. Fetch the page and read the verb
> in the original sentence. This rule exists because a first draft of the 40 Thorndike report
> asserted a day care had opened when it never did.

## 6. Special-permit numbers show up in more places than the obvious log, inconsistently formatted

A Planning Board number appears, inconsistently formatted, on far more datasets than the
"Development Log" family. `Building Permits: Addition/Alteration` (`qu2z-8suj`, field
`planning_board_number`) and `Building Permits: New Construction` (`9qm7-wbdc`, field
`special_permit_number`) both carry one — as free text mixed in with building-permit IDs and BZA
case numbers in the same field (`PB123`, `123`, `231A amendment #5`, `BZA-016894-2018`). For any
"every permit that touches X" question, check building permits too, and **strip `BZA`-prefixed and
long/dash-suffixed tokens** before treating a value as a PB number.

Older permit numbers are also inconsistently zero-padded across sources — `PB20` vs `PB020`,
`sp1` vs `sp01`. **Strip leading zeros (and prefix letters) before comparing or joining**, or
matches silently drop.

## 7. A spatial nearest-match is corroboration, not proof

DuckDB's `spatial` extension loads cleanly (`INSTALL spatial; LOAD spatial;`) and is useful for
polygon/point work. But a nearest-point join between two datasets that weren't designed to key off
each other (e.g. attributing an open-space polygon to the nearest Development Log project by
lat/lon) is **corroborating evidence only, not proof of attribution.** State the match distances
and flag the ambiguity rather than asserting a link the data doesn't actually encode.

> In the POPS analysis, a PUD-zone → nearest-project sweep surfaced 8 candidates; only 3 verified as
> real commitments on reading the actual decision. A majority of spatial leads turned out negative —
> the value was in ruling them out with the same rigor as the positives.

## 8. Addresses can be filed under the wrong number

`Cambridge Property Database` (`eey2-rv59`) files 40 Thorndike St under **`48 Thorndike St`**, so
a plain address search returns zero rows. **Resolve the address to a `map_lot` via
`Cambridge Address Points` (`4ftb-8ne5`, field `full_addr`) and query on `map_lot`** — the same
move that `52p4-36ct`'s compound `address` field forces.

## 9. Scanned PDFs have no text layer

City-hosted decision PDFs (Planning Board decisions, special permit filings) are often **scanned
images with no text layer** — `pdftotext` returns near-empty output and web-fetch can't extract
them. It isn't universal: newer CDD staff memos (2025 vintage) have a real text layer and
`pdftotext -layout` works. **Always try `pdftotext` first**, `wc -c` the output, and only fall
back to page-by-page image rendering if it comes back near-empty. For page counts on a scanned
file, `pdfinfo` is reliable where a naive `/Type /Page` byte regex is not.

## 10. "Developer commitments" is not a portal category

There is **no portal dataset of Planning Board special permit decisions.** `search_catalog` on
"special permit" / "planning board" surfaces only the already-checked `Board of Zoning Appeal
Requests` and an unrelated report. `Board of Zoning Appeal Requests` (`urfm-usws`) is a *false
friend* — its open-space fields measure a zoning density metric (usable open space as a percentage of
lot area), not public accessibility. The closest thing to a systematic index is the zoning-district
GIS layers, and even those locate *where* a zone applies, not *what* any given permit requires.

## 11. A dataset can be stale relative to its own source

The `Open Space` layer (`88i7-ga9f`) was last synced to Socrata 2024-11-27; its underlying GIS
source was edited 2026-06-16 — a seven-month-plus lag long enough that recently completed spaces are
missing from the public inventory. Surface freshness, and prefer `min`/`max` of a date field over a
dataset-level "last edited" timestamp when judging whether a query is current.

## 12. Don't assume a clean join will stay clean

`ixg8-tyau` (Budget – Salaries, field `department`) and `5bn4-5wey` (Budget – Operating
Expenditures, field `department_name`) joined on plain equality for FY2027 — 15 of ~17
departments, no normalisation. **Don't assume that holds for other dataset pairs;**
department/agency naming isn't consistently keyed portal-wide. Treat a clean join as a per-pair
result, not a guarantee.
