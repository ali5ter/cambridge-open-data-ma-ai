---
name: cambridge-open-data
description: Find, fetch, cross-reference, and infer insights from datasets on the Cambridge MA Open Data Portal (data.cambridgema.gov) when the user asks a question about Cambridge city data -- budget/finance, public safety, permitting, GIS/parcels, public health, schools, or similar civic datasets.
---

# Cambridge Open Data Portal

This skill drives the `cambridge_data` toolkit in this repo
(`src/cambridge_data/`, `scripts/`) to answer questions against
[data.cambridgema.gov](https://data.cambridgema.gov), a Socrata portal with 280+ public
datasets. Public dataset reads and catalog search need no credentials; `.env` holds an app
token that lifts the anonymous rate limit (see `.env.template`).

> A harness-agnostic mirror of this Skill -- the same body without the YAML frontmatter and the
> omp-specific tooling, for pasting into other harnesses -- lives at
> `skills/cambridge-open-data/SKILL.md`.

## Workflow

1. **Discover.** Search the local catalog cache first -- it's instant and covers name,
   description, category, and tags:

   ```bash
   cambridge-data search "<keyword>"
   ```

   If the cache is missing or looks stale for the question at hand, refresh it
   (`cambridge-data refresh`; ~280 rows, a few seconds). Read the printed
   `columns_*` metadata (available via `cambridge_data.catalog.get(dataset_id)`) before
   fetching -- it tells you field names/types without pulling data.

2. **Fetch.** Pull full dataset contents into the local Parquet cache:

   ```bash
   cambridge-data fetch <dataset-id>
   cambridge-data fetch <dataset-id> --where "fiscal_year='2027'"   # server-side filter
   ```

   Re-fetch is cheap and safe (overwrites); `data/manifest.json` records when each dataset
   was last pulled. Don't re-fetch a dataset already cached for the same question unless the
   data is time-sensitive (crime, 311, permits) and staleness matters -- check
   `manifest.json`'s `fetched_at` first.

3. **Cross-reference.** Open the DuckDB warehouse -- one SQL view per cached dataset, named
   `ds_<id-with-underscores>` -- and join/aggregate directly:

   ```python
   from cambridge_data import warehouse
   con = warehouse.connect()
   con.sql("""
       SELECT dept, SUM(TRY_CAST(total_salary AS DOUBLE))
       FROM ds_ixg8_tyau GROUP BY 1
   """)
   ```

   Every field comes back from Socrata as a string -- always `TRY_CAST` before numeric
   aggregation, and expect join keys (e.g. department names across datasets) to need
   normalization (case, whitespace, abbreviation mismatches) before they line up.

4. **Infer and deliver.** Default output mode is inline: answer in chat, save any charts
   under `data/charts/*.png` (matplotlib, `Agg` backend) and reference the path. Two other
   modes are available on request, not default:
   - **Markdown report** (the only mode that survives past the chat -- use it whenever the
     user asks for something to reference later, not just when asked for a "report"): write
     `docs/reports/<YYYY-MM-DD>-<slug>/report.md`, with any chart copied into that same
     directory (not left in `data/charts/`, which is gitignored/rebuildable) so the report is
     self-contained and git-tracked. Include a "Data provenance" section with dataset id(s),
     whether they were cached via `fetch_dataset.py` or queried ad hoc, and the key
     queries/filters used, so the finding is reproducible later.
   - **Design-brief handoff**: produce a structured brief (data summary, key findings,
     suggested chart types/narrative) sized for pasting into Claude Design or a similar tool
     -- use when the user wants a polished/presentation-grade visual, not a quick chart.

   For genuinely novel cross-dataset inference (as opposed to straightforward
   lookups/aggregates), prefer running that specific reasoning step through the strongest
   available model rather than the fast default -- civic data claims (budget, crime, housing)
   warrant care about confounders and overconfident causal language.

## Gotchas

- Socrata identifiers are "four-by-fours" like `ixg8-tyau` -- always the dataset id, not the
  friendly name.
- Discovery API (`catalog.py`) and SODA API (`client.py`) are different endpoints on different
  domains (`api.us.socrata.com` vs `data.cambridgema.gov`) -- both wrapped already, no need to
  hand-roll requests.
- `iter_all_rows` paginates automatically (50k rows/page); don't loop `$offset` by hand.
- Don't reach for `sodata-py` (the PyPI `socrata-py` SDK) -- it's the *publishing/ETL* SDK
  (revisions, uploads, transforms), not a fit for read-only analysis.
- Before answering a question that hinges on one field (payment status, disposition, a
  numeric total), check that field's actual population, not just its presence in the schema:
  `SELECT count(field), count(*) WHERE field IS NOT NULL` plus `min/max` of the date column
  for rows where it's populated. Socrata datasets often carry a field that's only populated
  for a recent operational window, or absent for most of the dataset's history -- silently
  computing a rate/total over all rows in that case understates or fabricates the answer.
- The catalog's `columns_name` (display names, e.g. `Planning Board Special Permit`) is not
  the field to query with -- the SODA API only accepts `columns_field_name`
  (e.g. `pb_special_permit`). Querying or joining on a display-derived guess doesn't error,
  it silently returns zero rows, which reads as "no match" rather than "wrong field name."
  Always confirm against `columns_field_name` before writing a `$where`/`$select` or a join.
- Cambridge's older permit/case identifiers (special permit numbers, some project codes) are
  inconsistently zero-padded across sources -- `PB20` vs `PB020`, `sp1` vs `sp01`. Strip
  leading zeros (and prefix letters) before comparing/joining on them, or matches silently
  drop.
- City-hosted decision/report PDFs (Planning Board decisions, special permit filings) are often
  scanned images with no text layer -- `pdftotext` returns near-empty output and WebFetch can't
  extract them. This isn't universal, though: newer CDD staff memos (2025 vintage confirmed) have
  a real text layer and `pdftotext -layout` works directly. Always try `pdftotext` first --
  `wc -c` the output, and only fall back to downloading + the file-reading tool's page-by-page
  image rendering if it comes back near-empty. For page counts on a scanned one, `pdfinfo` is
  reliable where a naive `/Type /Page` regex on the raw bytes is not (older scans use object
  streams that hide the count from a byte-level regex).
- A Planning Board special permit number shows up, inconsistently formatted, on far more
  datasets than the obvious "Development Log" family -- `Building Permits: Addition/Alteration`
  (`qu2z-8suj`, field `planning_board_number`) and `Building Permits: New Construction`
  (`9qm7-wbdc`, field `special_permit_number`) both carry one, as free text mixed in with
  building-permit IDs and BZA case numbers in the same field (`PB123`, `123`,
  `231A amendment #5`, `BZA-016894-2018`, a bare 6-digit permit ID). For any question that hinges
  on "every permit that touches X," check building-permit datasets too, not just the
  purpose-built log -- this surfaced two real special permits (PB-315, PB-371) with public-space
  commitments that neither CDD's own POPS index nor the Development Log's free text mentioned.
  Filter out BZA-prefixed and long/dash-suffixed tokens before treating a value as a PB number.
- Before concluding "no permits found" for an address/parcel, check *dataset* date coverage,
  not just field population within one dataset. `Building Permits: Addition/Alteration`
  (`qu2z-8suj`) and `Building Permits: New Construction` (`9qm7-wbdc`) only start 2018-07 --
  older work lives in `Building Permits: 1 and 2 Family - DEPRECATED` (`52p4-36ct`, covers
  2013 through 2018-07, one-and-two-family only). The two eras don't share a schema: field
  names differ (`plannumber`/`applicationdate`/`class` vs `id`/`issue_date`/`permit_type`) and
  the deprecated dataset's `address` field is a compound Location type -- `upper()`/`LIKE`
  against it 400-errors from Socrata. Match on `parcelnumber` (equivalent to `mbl`/`map_lot`
  elsewhere) instead. A `min(date_field)`/`max(date_field)` sanity check against any permit,
  case, or complaint dataset before trusting a zero-result address search would catch this
  class of gap immediately -- run it as routinely as the field-population check above.
- For "find every permit/project that touches X" questions, a zoning GIS layer can out-perform
  keyword search entirely: `Community Development Department Zoning Districts` (`yc3q-q3hf`) has
  a `pud_type` field enumerating every Planned Unit Development zone in the city -- spatially
  matching each zone's centroid to the nearest Development Log project (corroborating only, same
  caveat as any nearest-point join) surfaced real permits that no free-text keyword scan found.
  This is a fundamentally different, more systematic discovery method than grepping notes for a
  hoped-for phrase -- worth reaching for first when the question is "find every X," not as a
  follow-up. Expect a high false-positive rate on the nearest-project match itself, though: of 8
  candidates surfaced this way, only 3 verified as real commitments on reading the actual
  decision -- always verify against the decision, never report a spatial-match candidate as a
  finding on its own.
- DuckDB's `spatial` extension (`INSTALL spatial; LOAD spatial;`) loads cleanly and is useful
  for polygon/point work (`ST_Area_Spheroid`, `ST_Distance_Spheroid`, `ST_Centroid`,
  `ST_GeomFromGeoJSON` on a dataset's `the_geom` column) -- but treat a nearest-point spatial
  join as corroborating evidence only, not proof of attribution, when the two datasets weren't
  designed to key off each other (e.g. attributing an open-space polygon to the nearest
  Development Log project by lat/lon). State match distances and flag ambiguity rather than
  asserting a link the data doesn't actually encode.
- **Separate an *existence* claim from a *status* claim, and verify them differently.** "The
  decision contains this condition" / "the Council order lists this commitment" is settled by
  reading the document. "It was built / opened / leased / paid" is not -- a document or
  announcement only establishes intent as of its own date. Sources describing a delivery are
  almost always dated *at* the delivery and are often promotional (developer press release,
  ribbon-cutting coverage), and nobody circles back to report the thing that quietly didn't
  happen. Before writing that something was delivered: (1) run a search bounded to *after* the
  claimed date -- "still vacant," "one year on," the following year's coverage; (2) check the
  counterparty's own website, since an organisation that genuinely operates a facility says so
  on its own site. This is the same shape as the special-permit gotcha above (a permit's
  presence doesn't imply an enforceable condition), one link further down the chain: an
  obligation's existence doesn't imply its delivery. Concretely: the 40 Thorndike report first
  asserted that a childcare facility run by East End House opened with the building in 2024-10.
  It never opened -- the original wording was "*future* first-floor... day care space" and
  "*will open* this fall," and the space still "remains vacant" per the developer's own
  representative nine months later, while East End House was separately campaigning to replace
  its own condemned building via an unrelated developer's project. Corollary: **never let a
  WebFetch summary carry a status claim** -- WebFetch answers via a small fast model, which
  reliably flattens future tense into past. `curl` the page and read the verb in the original
  sentence.

## Self-Audit (keep this file current)

This file is a living artifact, not a one-time scaffold -- it improves by being edited, not by
a background process. After any substantive use (skip this for trivial single-query lookups):

1. **Audit in one or two sentences**: did catalog search surface the right dataset on the
   first try? Did a join key need unexpected normalization? Did a query error, get throttled,
   or return something misleading (spurious correlation, wrong fiscal year, stale cache)?
2. **Durable and reusable** -> edit Workflow/Gotchas above directly. This file should always
   read as current best practice, not as an append-only log.
3. **One-off but worth remembering** (a specific dataset's quirk, a join-key mapping that
   worked) -> add a dated bullet under Field Notes. Cap it around 15 entries -- prune stale or
   superseded ones, and promote anything that recurs twice into Gotchas instead of leaving it
   in the list.
4. Don't use omp's `learn`/`manage_skill` tools for this even if available: they write to
   `~/.omp/agent/managed-skills/`, a separate global namespace that authored skills like this
   one always shadow in discovery -- edits there would never take effect. Edit this file
   directly with the normal edit tool.

## Field Notes

- 2026-08-05: `ixg8-tyau` (Budget - Salaries, field `department`) and `5bn4-5wey` (Budget -
  Operating Expenditures, field `department_name`) joined cleanly on plain equality for
  FY2027 -- 15 of ~17 departments matched, no normalization needed. Don't assume that holds
  for other dataset pairs; department/agency naming isn't consistently keyed portal-wide.
- 2026-08-05: `vnxa-cuyr` (Cambridge Parking Tickets, 3.07M rows since 2014) has no payment
  or disposition field. `amount_due` is only populated for tickets from 2025-07-01 onward
  (146,261 of 3.07M rows) and means *current outstanding balance*, not the original fine --
  it's `0` for both paid and voided/dismissed tickets (indistinguishable from each other) and
  includes escalated late fees for unpaid ones, so it can't be summed into a "revenue lost"
  figure at face value. Also: `violation_description` values differ by era -- full text like
  `STREET CLEANING` in the historical bulk data, truncated to 10 chars (`STREET CLE`) in the
  2025 H2 window -- match both when filtering by violation type.
- 2026-08-09: `88i7-ga9f` (Open Space) has an `FCODE` field the dataset's own metadata doesn't
  document -- the linked GIS Data Dictionary page renders its code table as an embedded image,
  not text. Decode it from the page's base64-encoded inline JPEG (or the ArcGIS/CDD map legend
  PDF) rather than guessing from context; a few codes seen in the data (13, 45) are absent even
  from the decoded dictionary. Development Log free-text fields (`note`, `project_description`)
  do not mention public-access/POPS commitments even where one exists per the governing permit
  -- text-mining them for that is a dead end; the permit number is the only reliable link, and
  even that requires reading the actual decision PDF, since a permit's presence doesn't imply
  it contains an enforceable access condition (many only have Findings, which are not
  binding).
- 2026-08-10: The current-edition Development Log (`wjwg-93qh`) names its special-permit column
  `planning_board_special_permit`, not `pb_special_permit` like the two historical Dev Log
  tables (`a5ud-8kjv`, `5432-hmix`) -- same concept, different field name across otherwise
  sibling datasets. A cross-table union/join needs an explicit per-table column alias, not one
  shared field name. Also: free-text `note`/`project_description` fields aren't *always* a dead
  end for POPS language -- one recent project row (PB-315, 2025-2026 completions) explicitly said
  "grade level public open space." Worth a keyword scan across free text before ruling it out on
  a given question, just don't rely on absence of a hit as absence of a commitment. A second pass
  over `Building Permits: Addition/Alteration` and `Building Permits: New Construction` (see
  Gotchas) found PB-371 (MIT, 269-301 Vassar St) the same way -- confirmed against its decision
  PDF, Condition 5, a real recorded-easement requirement. `Board of Zoning Appeal Requests`
  (`urfm-usws`) looked promising on field names alone (`requested_usable_open_space_ratio` etc.)
  but is a false friend for POPS questions -- that's zoning-required *private* usable-open-space
  ratio (a lot-coverage/density metric everyone must satisfy), unrelated to public accessibility;
  it also carries no Planning Board permit field. `Master Addresses List` (`vup6-kpwv`) is pure
  geocoding (building IDs, census/police/election districts) -- no permit or open-space field,
  not useful for permit-cross-reference questions at all.
- 2026-08-10: A third pass, this time via the `yc3q-q3hf` PUD zoning layer (see Gotchas), found
  3 more real permits with a public-access condition (PB-175, PB-286, PB-303) and ruled out 5
  candidates on reading their actual decisions -- PB-233 turned out to be a denied application
  (a denied permit has zero Conditions, whatever its Findings discuss), PB-192 and PB-354 had
  Findings that explicitly reason *against* public access ("might seriously compromise the
  amenity value... for residents" / open space "for the occupants," not the public) -- a useful
  reminder that a Finding mentioning open space doesn't even weakly suggest a public-access
  Condition exists; sometimes it's evidence of the opposite. PB-303 also introduced a fourth
  distinct open-space legal mechanism beyond the three already known (CRA/MXD §14.40, University
  Park §15.41, Harvard letter): a PUD's own zoning-ordinance section (here §13.87.1) can carry
  its own district-wide "Publicly Beneficial Open Space" requirement, textually similar to
  University Park's but codified per-PUD -- check the specific PUD's governing ordinance section
  rather than assuming all PUD open-space obligations trace to one of the mechanisms already
  found.
- 2026-08-10: For "what agreements exist about building X" questions, expect **three separate
  legal instruments** that portal data barely touches, and don't conflate them: the Planning
  Board special permit (zoning; conditions may *require* a lease without being one), a municipal
  property disposition under M.G.L. Ch. 30B + Municipal Code Ch. 2.110 (how the City leases or
  sells its own property -- needs a two-thirds Council vote, produces a City Manager Disposition
  Report and an RFP, and is where the real money terms live), and floor amendments extracted at
  the Council vote itself (binding in practice, but often existing only in the hearing record and
  press coverage -- not in any filed document). At 40 Thorndike/PB-288 the entire East End House
  childcare commitment lived only in the third category. Useful entry points: CDD's per-permit
  index at `cambridgema.gov/specialpermits/pb<NNN>` (reliable, lists every filing) and
  `cambridgema.gov/firststreetgarage`-style City Manager project pages -- though the latter can
  be badly stale (that one has no substantive update after 2019-12, five years of silence on
  whether any commitment was honoured). Council hearing records aren't on the portal at all;
  the `rwinters.com/council/<MMDDYY>.htm` civic archive mirrors City Manager letters verbatim
  and is the only searchable full text found (note: its TLS cert doesn't match the hostname, so
  WebFetch refuses it -- `curl -k` works). Dataset quirk: `eey2-rv59` files 40 Thorndike St
  under `48 Thorndike St`, so an address search returns zero rows -- resolve the address to a
  map-lot via `4ftb-8ne5` (`full_addr`) and query on `map_lot` instead, as with `52p4-36ct`.
