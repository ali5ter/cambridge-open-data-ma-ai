---
layout: home
hero:
  name: Cambridge Open Data Portal Tools
  text: An MCP server, an AI Skill, and Python scripts for civic-data analysis
  tagline: Ask an AI agent a question about Cambridge civic data; get a cross-dataset answer.
  actions:
    - theme: brand
      text: Get started
      link: /getting-started.html
    - theme: alt
      text: Read the gotchas
      link: /gotchas.html
features:
  - title: Eight tools, four resources
    details: Discover, fetch, cross-reference, and query the Socrata portal as an MCP server.
  - title: A Skill to help assist finding and interpretation
    details: In combination with the MCP server, facilitates correct retrieval of data within the Portal and external sources linked from the Portal.
  - title: Tutorials
    details: Examples of how the Python scripts, and Skill have been used.
  - title: No credentials
    details: Public dataset reads and catalog search work without credentials.
  - title: One source of truth
    details: The MCP server, the Skill, and Python scripts share a single library.
  - title: Tests included
    details: Smoke tests provided to verify whether the tooling works.
---

The Cambridge MA Open Data Portal ([data.cambridgema.gov](https://data.cambridgema.gov)) is a
Socrata instance with **280+ public datasets** — budget, public safety, permitting, GIS/parcels,
public health, schools, and more. This project makes that data usable by an AI agent through two
complementary interfaces that ship as one unit:

- **An MCP server** (`cambridge_data.mcp`, console script `cambridge-open-data-ma-mcp`) — the
  *machine* interface: eight tools and four resources that an AI agent can use to discover, fetch,
  cross-reference, and query the Portal.
- **A Skill** (`.claude/skills/cambridge-open-data/SKILL.md`) — the *cognitive* interface: the
  discover → fetch → cross-reference → infer workflow working around know gotchas already found when working with with data in the Portal.

The server wraps the same library the `cambridge-data` CLI calls, so the harness and the CLI never
drift — **one source of truth** serves every entry point. Public dataset reads and catalog search
work with **no credentials**.

> [!TIP]
> New here? Start with [Getting started](getting-started.md), then read the
> [workflows](concepts.md) and the [gotchas](gotchas.md) before trusting any responses the toolkit
> returns.

## What you can ask

Five worked use-cases are included as tutorials, each grounded in a real analysis run against the
portal. They double as the toolkit's test-suite:

| # | Question | What it teaches |
|---|---|---|
| 1 | FY2027 salary vs. operating budget, by department | A clean cross-dataset join (`ixg8-tyau` ⋈ `5bn4-5wey`) |
| 2 | Are street-cleaning parking tickets paid? What's the revenue lost? | The **recent-window trap** — a field populated for 4.8% of rows |
| 3 | Which private spaces are open to the public, and under what rules? | **Spatial discovery** + reading scanned decisions (the largest analysis here) |
| 4 | What does the portal know about 80 Thorndike St? | The **era gap** — current permit datasets start 2018-07 |
| 5 | What did the developer of 40 Thorndike St promise the City? | **Civic agreements aren't portal data** + **existence ≠ delivery** |

[Open the tutorials](tutorials/01-budget-salary-vs-operating.md). After the five analyses,
[tutorial 6](tutorials/06-drive-the-skill-in-opencode.md) shows the whole loop driven from a
harness -- the Skill in opencode, with the MCP tool calls that produce the answer.

## Install in one line

From a clone of this repo, with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run scripts/refresh_catalog.py     # pull the 280+ dataset index (a few seconds)
uv run scripts/mcp_smoke.py           # end-to-end check (14/14 with a populated cache)
```

See [Install and register](install.md) for every harness -- opencode, Claude Code, Cursor,
Cline/Roo, Codex, Gemini CLI, and Antigravity -- and the HTTP bridge for OpenWebUI, ChatGPT, and
Claude.ai.

## Layout

```text
docs/                      this site
  index.md                 you are here
  install.md               register the server across harnesses + deliver the Skill
  getting-started.md       first cross-dataset question, end-to-end
  concepts.md              discover → fetch → cross-reference → infer, plus the guards
  gotchas.md               the failure modes that make civic-data answers wrong
  reference.md             the 8 tools and 4 resources
  configuration.md         .env, cache/reports directories
  tutorials/               the five worked use-cases plus a harness how-to
src/cambridge_data/        the library + the MCP server + the cambridge-data CLI (one source of truth)
scripts/                   per-operation helpers (by-hand equivalents of cambridge-data)
opencode.json              the shareable server registration
```
