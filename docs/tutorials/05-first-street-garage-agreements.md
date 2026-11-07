# Tutorial 5 — What did the developer of 40 Thorndike St promise the City?

> **Question.** Find all references to agreements related to 40 Thorndike Street and the First
> Street Garage with East End House — special permits, leases, or commitment letters — plus any
> other commitments Leggat McCall Properties made to the City of Cambridge.

This is the tutorial to read for the two hardest lessons in the whole toolkit: **civic agreements
aren't portal data**, and **existence is not delivery**. It is also the one that carries a built-in
correction — a first draft got it wrong, and the fix is the lesson.

## The honest bottom line, up front

**None of this exists as structured data on the Open Data Portal** — it had to be assembled from
zoning decisions, a City Manager's disposition report, a CDD staff memo, a Council hearing record,
and news coverage. The portal contributes **parcel/ownership corroboration only.**

40 Thorndike St (the former Sullivan Courthouse) was redeveloped by Leggat McCall Properties (LMP)
under **Planning Board Special Permit PB-288** (2014, amended 2020). The East End House connection
is the **sole origin of a Council floor amendment** — Councillor Siddiqui made her deciding 6–3
vote on 2019-09-18 conditional on, among other things, *"a good faith effort by the company to
fulfill a promise for child care by finding a local nonprofit to run it."* No permit condition,
Council order, lease, or commitment letter **names East End House anywhere** — and the childcare
commitment was **never fulfilled**: the space was still vacant as of July 2025.

## The three legal instruments (don't conflate them)

> **Gotcha — civic agreements are not portal data.** Expect **three separate instruments**:

1. **The special permit** (PB-288, zoning). Condition 6 *requires a long-term lease* for up to 420
   parking spaces in the City-owned First Street Garage — it **requires a lease to exist; it is not
   the lease.**
2. **The municipal property disposition** (M.G.L. Ch. 30B + Municipal Code Ch. 2.110; a two-thirds
   Council vote, a City Manager Disposition Report, an RFP). This is where the **money terms
   live** — a bid valued at ~$77.4M (parking/retail lease revenue over 30 years, capital
   contributions, $8M to the Affordable Housing Trust, 48 affordable units), in exchange for
   surrendering 150 of 420 parking spaces.
3. **Floor amendments** extracted at the Council vote — binding in practice, but existing only in
   the hearing record and press coverage, in **no filed document.** The childcare commitment is
   here, and nowhere else.

The two buildings are linked entirely by **parking**: 40 Thorndike couldn't fit enough parking on
its own site, so its permit lets it satisfy the shortfall with leased spaces in the neighbouring
City-owned garage.

## The correction, and the lesson: existence ≠ delivery

A first draft of this analysis stated that 40 Thorndike "opened in October 2024 with a day care run
by East End House." **Both claims were wrong.** They came from press coverage written in the
future tense — "*future* first-floor restaurant and day care space," "*will open* this fall" —
mis-summarised as completed fact. The primary sources say the opposite: as of **July 8, 2025**,
nine months after opening, LMP's own representative confirmed the first-floor day care
**"[remains vacant](https://www.cambridgeday.com/2025/07/08/)."**

> **Gotcha — never let a WebFetch summary carry a status claim.** WebFetch answers via a small
> fast model that reliably flattens *future tense into past.* "*Future* day care space" and
> "*will open* this fall" both collapse into "opened." For any claim that something was *delivered*,
> fetch the page and **read the verb in the original sentence.** A follow-up search bounded to
> *after* the claimed date — "still vacant," "nine months on," the next year's coverage — is the
> cheapest way to catch it. That single query is what broke this open.

Checking each 2019 commitment against primary sources:

| Commitment | Status (2026) |
|---|---|
| Childcare space (East End House) | **Not delivered** — "remains vacant" per LMP, July 2025 |
| Senior/community space | Partial, unverified — exists at First Street Market, but neither party claims East End House runs it |
| Garage retail activation | Delivered — Amba Café (May 2024), First Street Market (Aug 2024) |
| 48 affordable units | Delivered but lagging — built, only 17 of 48 occupied at 9 months |
| $8M Affordable Housing Trust | **Unverified** — no public confirmation of payment found |

Meanwhile, East End House is fighting to replace its *own* condemned building at 105 Spring St via
an unrelated developer's project — an organisation that had just been given a new facility one block
away would not be campaigning that way.

## The structured cross-reference (what the portal *can* do)

The portal does confirm the parcels and their linkage, independently of the document trail:

- The Development Log (`5432-hmix`, `a5ud-8kjv`) carries project 403, "Sullivan Courthouse
  Redevelopment," developer "Leggat McCall," `pb_special_permit = PB288`, with the note
  *"Parking includes 85 spaces on-site and 270 spaces leased at First St Garage"* — the **only**
  mention of the garage lease in any structured Cambridge dataset.
- `Cambridge Address Points` (`4ftb-8ne5`) geocodes 40 Thorndike St → map-lot `19-22`,
  55 First St → `18-75`.
- `Cambridge Property Database` (`eey2-rv59`), **by map-lot** (a plain address search for "40
  Thorndike" returns nothing — it's filed as `48 Thorndike St`), shows `19-22` transitioning from
  `MIDDLESEX COUNTY OF` to `LMP GP HOLDINGS LLC`, and `18-75` as `CAMBRIDGE CITY OF` throughout —
  confirming the Garage remains City-owned, consistent with a leasehold rather than a sale.

## What this tutorial demonstrates

- **Civic agreements aren't portal data** — the #4 gotcha, and why a question like "what did the
  developer promise" can't be answered from Socrata.
- **The three-instrument model** — special permit / disposition / floor amendment, each with a
  different home and a different evidentiary weight.
- **Existence is not delivery** — the #5 gotcha, and why every "delivered" claim must be
  re-verified against primary text *after* the claimed date.
- **Honest provenance** — the report lists every URL and flags which are scanned, which are stale
  (the City's own updates page has no substantive update after December 2019), and which require a
  browser user-agent.

See the full report (three charts, the complete source table, the methodology) in the upstream
`local-data-experiments` repo:
`docs/reports/2026-08-10-40-thorndike-east-end-house-agreements/`.
