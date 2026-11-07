# Tutorial 4 — A full property profile: 80 Thorndike St

> **Question.** What does the Cambridge Open Data Portal contain about 80 Thorndike St, Cambridge,
> MA 02141 — cross-referencing property, permit, and service-request datasets?

This tutorial is about the **era gap**: the portal's *current* permit datasets start 2018-07, so a
naive query makes it look like no renovation happened — when in fact a $308,500 gut renovation in
2016 lives in a deprecated dataset most searches skip. It also covers the address-filing trap.

## The property record

Source: `Cambridge Property Database FY2016-FY2026` (`eey2-rv59`), PID 1176, GIS ID / Map-Lot
`24-41`. Single-family residential, built 1854, 2,347 sq ft, 2.5 stories, zoning C-1. The Land Use
layer (`dnyu-v8e9`), Parcel Data (`c392-hjk3`), and Address Points (`4ftb-8ne5`, Building ID
`497-2`) independently confirm the parcel — all three agree on map-lot `24-41`.

Owner of record: Alister & Abigail Lewis-Bowen, last sale **$850,000 on 2013-02-25**. Assessed
value nearly doubled over eleven years, from $850,700 (FY2016) to $2,080,800 (FY2026).

## Step 1 — resolve the address to a parcel, don't query the address

> **Gotcha — addresses can be filed under the wrong number.** `eey2-rv59` files *40* Thorndike St
> under **`48 Thorndike St`**; a plain address search returns zero rows. The fix, general for any
> address lookup: resolve the address to a `map_lot` via `Cambridge Address Points`
> (`4ftb-8ne5`, field `full_addr`), then query on `map_lot` — the same move the deprecated permits
> dataset forces (see Step 3).

```sql
-- resolve 80 Thorndike St -> map_lot
SELECT ml FROM ds_4ftb_8ne5 WHERE full_addr LIKE '%80 THORNDIKE%';   -- -> '24-41'
```

## Step 2 — the era gap: query *both* permit generations

The portal's current-generation permit datasets cover only work from **2018-07** onward. A first
pass against just those found exactly one permit (a 2019 window replacement) and looked like no
2014-era remodeling had happened. **That's a coverage gap, not an absence of permits.** Older
one- and two-family permits live in a separate, deprecated dataset with a *different schema*.

| Dataset | id | Covers | Schema |
|---|---|---|---|
| Building Permits: Addition/Alteration | `qu2z-8suj` | 2018-07 → | `id`, `issue_date`, `permit_type`, `mbl` |
| Building Permits: New Construction | `9qm7-wbdc` | 2018-07 → | `id`, `issue_date`, `permit_type`, `mbl` |
| Building Permits: 1 and 2 Family — **DEPRECATED** | `52p4-36ct` | 2013 → 2018-07 | `plannumber`, `applicationdate`, `class`, `parcelnumber` |

The two eras don't share a schema, and the deprecated dataset's `address` field is a compound
`Location` type that **400-errors on `LIKE`/`upper()`** — match on `parcelnumber` (equivalent to
`mbl`/`map_lot` elsewhere) instead:

```sql
-- older permits, matched on parcel, not address
SELECT plannumber, applicationdate, class, cost
FROM ds_52p4_36ct
WHERE parcelnumber = '24-41'
ORDER BY applicationdate;
```

The full history across both generations:

| Filed | Permit ID | Class | Cost | Description | Source |
|---|---|---|---:|---|---|
| 2013-03-15 | `BLDR-000618-2013` | Roof | $4,250 | New asphalt shingle roof | `52p4-36ct` |
| 2013-04-01 | `BLDR-000712-2013` | Roof | $2,474 | Shingle re-roof + 2 skylights | `52p4-36ct` |
| 2013-04-03 | `BLDR-000740-2013` | Roof | $6,950 | Demo/rebuild main chimney | `52p4-36ct` |
| **2016-02-23** | **`BLDR-009493-2016`** | **Addition/Alteration** | **$308,500** | **Gut renovation: demo to studs, asbestos abatement, full re-framing, new gas boiler + AC, insulation, new flooring** | `52p4-36ct` |
| 2017-11-09 | `BLDR-014992-2017` | Addition/Alteration | $17,280 | Solar install, 18 panels | `52p4-36ct` |
| 2019-06-13 | `48444` | Addition/Alteration | $6,000 | 3 replacement windows | `qu2z-8suj` |

The $308,500 permit is almost certainly the significant remodel — by cost and scope it dwarfs
everything else, which is otherwise roofing and solar. The FY2017→FY2018 assessed-value jump
(+29%) lines up with the year after the 2016 permit — a correlation worth noting, not a proven link
(the assessor re-values improvements the year after major work is recorded, but the dataset doesn't
state that as cause and effect).

> **Gotcha — check the dataset's own date coverage before trusting a zero.** The portal-wide floor
> for *any* Cambridge property in the deprecated permits dataset is 2013-02-25 (coincidentally the
> same day as this property's purchase). Nothing on the portal documents work done to the house
> across the prior owner's 17 years (1996–2013); if it changed hands before 1996, that predates the
> portal entirely.

## Step 3 — cross-reference the other datasets

- **311 service requests** (`Commonwealth Connect Service Requests`, `2z9k-mv9g`): nine requests
  2016–2022. A naive `LIKE '%80 Thorndike%'` also catches "180 Thorndike" — filter it out.
- **Crime Reports** (`xuad-73uj`): *cannot* be tied to a specific address — published at
  neighbourhood granularity only, by design.
- **Housing Permits** (`6nxj-uqfe`): no net unit change — consistent with a renovation that
  didn't add/remove units.

## What this tutorial demonstrates

- The **era gap** — the #3 gotcha: a zero-result search often means "wrong dataset era," and the
  fix is to query *both* generations.
- The **address-filing trap** — resolve to `map_lot`, don't query the address.
- **Correlation vs. causation** — the value jump is a correlation the data doesn't assert as cause.
- The discipline of checking the dataset's own `min`/`max` date before trusting an absence.

See the full report (chart, the assessed-value history, the before-2013 ownership, the complete
provenance table) in the upstream `local-data-experiments` repo:
`docs/reports/2026-08-10-80-thorndike-street-property-profile/`.
