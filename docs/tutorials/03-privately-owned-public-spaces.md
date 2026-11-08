# Tutorial 3 — Cambridge's privately owned public spaces (POPS)

> **Question.** Which private facilities in Cambridge are open to the public because of commitments
> developers made during permitting, and what are the rules and contacts for using them?

This is the largest analysis in the corpus — and the one that best shows the toolkit doing what it
was built for: **spatial discovery** across datasets that were never designed to talk to each
other, plus the judgment that separates a finding from a guess. Read
[gotchas](../gotchas.md) first; this tutorial is where most of them pay off.

## The answer, up front

The city's own term of art is **POPS — "Special Permit Privately Owned Public Spaces."** The
portal's `Open Space` layer maps **28 such spaces**, and CDD separately lists **13 special permits**
plus **3 other legal mechanisms** as the basis for public access. The portal answers *where* well
and *what are the rules* almost not at all:

- **No dataset carries hours, permitted uses, prohibited uses, signage, maintenance responsibility,
  or a contact.** CDD's own guidance is "contact the property manager" — without naming one.
- Reading the 13 governing decisions directly shows why: **6 of the 13 impose no enforceable
  public-access condition at all** — the space exists only in the Board's *Findings* (the reasoning
  used to justify a height/FAR bonus), never converted into a binding term.
- One exception: the Cambridge Redevelopment Authority publishes actual hours, maintainer, and
  amenities for **14 named spaces** in the Kendall Square MXD district — the only place in any
  Cambridge source where POPS operating hours are public data.

## Step 1 — discover the spatial layer

`cambridge-data search "open space"` surfaces `88i7-ga9f` (Open Space, 249 polygons). Read its
schema — the machine field names a query accepts, plus the `the_geom` geometry column — and cache it:

```bash
cambridge-data search "open space"
cambridge-data describe 88i7-ga9f --probe
cambridge-data fetch 88i7-ga9f
```

The `owner` field breaks down as City 104, State 77, **Private 39**, Easement 1, and others. The
`fcode` field classifies 28 of the 40 Private/Easement rows as publicly-accessible-by-design
(codes 41–45).

> **Gotcha — undocumented codes.** The `FCODE` decode table lives only as an *embedded JPEG* on a
> GIS Data Dictionary page, and even that omits codes present in the data (13, 45). Decode it from
> the page's base64-encoded inline image, or the CDD map-legend PDF — not from context.

## Step 2 — inventory from geometry

DuckDB's spatial extension gives polygon area from the stored GeoJSON:

```sql
INSTALL spatial; LOAD spatial;
SELECT name, owner, fcode,
       ST_Area_Spheroid(ST_GeomFromGeoJSON(the_geom)) * 10.7639 AS sqft
FROM ds_88i7_ga9f
WHERE owner IN ('Private', 'Easement')
ORDER BY TRY_CAST(fcode AS INT), name;
```

The `cambridge-data query` subcommand can't run this: it executes a single `SELECT` over the cached
`ds_*` views and does not `INSTALL spatial`, so geometry work opens its own connection with
`warehouse.connect()` and runs the statement above. (The same reason the 3M-row live pull in
[tutorial 2](02-parking-ticket-payment-status.md) stays in Python — the CLI's `query` is
cache-only and non-spatial.)

## Step 3 — join to permits (and hit the naming traps)

The Development Log tables (`a5ud-8kjv`, `5432-hmix`, `wjwg-93qh`) carry a special-permit field
that joins to CDD's 13 permit numbers once **zero-padding is normalised** (`PB020`, not `PB20`).
Nine of the thirteen join this way; the four pre-1990 permits have a blank field and were matched
by exact project address instead.

Two naming traps, both in [gotchas](../gotchas.md):

- **The field name differs across sibling datasets.** The current-edition Development Log
  (`wjwg-93qh`) calls it `planning_board_special_permit`; the two historical tables call the same
  concept `pb_special_permit`. A cross-table union needs a per-table alias, not one shared name.
- **Special-permit numbers show up in more places than the log.** `Building Permits:
  Addition/Alteration` (`qu2z-8suj`, field `planning_board_number`) and `Building Permits: New
  Construction` (`9qm7-wbdc`, field `special_permit_number`) both carry one, as free text mixed in
  with building-permit IDs and BZA case numbers. Strip `BZA`-prefixed and long/dash-suffixed
  tokens before treating a value as a PB number.

## Step 4 — read the decisions (the judgment the tools can't do)

All 13 governing decisions are **scanned image PDFs with no text layer** — `pdftotext` returns
near-empty output. Each was downloaded and read page-by-page. This step distinguishes a numbered,
enforceable **Condition** from a **Finding** (the Board's non-binding reasoning for granting a
bonus). That distinction turned out to be the single most consequential fact about every permit.

> **Gotcha — spatial nearest-match is corroboration, not proof.** A PUD-zone → nearest-project sweep
> (`ST_Distance_Spheroid` between a zoning polygon's centroid and a Development Log project's
> lat/lon) surfaced 8 candidate permits; **only 3 verified as real commitments on reading the
> decision.** A majority of spatial leads turned out negative — the value was in ruling them out
> with the same rigor as the positives, never in assuming "near a PUD" implies a commitment.

## Step 5 — the addendum: a third, more systematic discovery pass

Passes 1 (Development Log free text) and 2 (Building Permits free text) both depend on a permit
leaving a keyword somewhere. A third, systematic route: the `CDD Zoning Districts` layer
(`yc3q-q3hf`) carries a `pud_type` field enumerating every Planned Unit Development — and PUDs are
the mechanism behind several POPS permits already found. Spatial matching each PUD centroid to its
nearest project surfaced **3 more real permits CDD's own list omits**:

- **PB-175** (North Point / Archstone) — Condition #10, active today;
- **PB-303** (MIT Kendall "SoMa" PUD-5) — adds a *fourth* legal mechanism (PUD-5's own
  Zoning Ordinance §13.87.1, alongside the CRA's MXD §14.40, University Park's §15.41, and the
  Harvard letter);
- **PB-286** (75 New Street) — a real but *contingent* Condition, not yet active.

The count is therefore **at least 17 active special permits plus 1 contingent, not 13.**

## The headline, and its corollary

The headline finding: **6 of 13 decisions impose no enforceable access condition at all** — the
space exists only in Findings used to justify a height/FAR bonus. The corollary for *using* these
spaces: a resident standing at the Broad Canal Walkway has no way to know it's a public right
unless they've read this report. No dataset flags a space as "POPS," and CDD's own map links point
at a dead URL path (`SpecialPermits` → `specialpermitsadvisory`).

## What this tutorial demonstrates

- The `cambridge-data` CLI doing discovery and caching (`search` / `describe` / `fetch`), with the
  spatial and scanned-PDF steps it can't cover left in Python.
- **Spatial discovery** across datasets that don't key off each other — the toolkit's signature
  capability, and why a *zoning-layer sweep* beats a keyword grep for "find every X."
- The **Finding-vs-Condition** judgment: a space mentioned in reasoning is not a space you can
  legally rely on.
- **Scanned-PDF handling** (try `pdftotext`, fall back to image rendering).
- Three discovery passes, each more systematic than the last, and the honesty of reporting the
  negatives.

See the full report (chart, all 28 spaces, the 13-permit findings table, the CRA shapefile, and
14 recommendations) in the upstream `local-data-experiments` repo:
`docs/reports/2026-08-09-publicly-accessible-private-spaces/`.
