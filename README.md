# cambridge-open-data-ma-ai

An **MCP server**, a **Skill** to enable an AI agent or agentic harness to discover, fetch,
cross-reference, and infer insights from the
[Cambridge MA Open Data Portal](https://data.cambridgema.gov); a Socrata portal with 280+ public
datasets (budget, public safety, permitting, GIS/parcels, public health, schools, and more).

This enables a natural-language question about Cambridge civic data and get back an answer built from
real cross-dataset analysis.

## What do you get?

- **An MCP server** — `cambridge_data.mcp`, exposed as the `cambridge-open-data-ma-mcp` console
  script: an 8-tool / 4-resource FastMCP (v1) server. It is the *agent-facing* interface, wrapping
  the same shared library (`src/cambridge_data/`) that the five command-line scripts
  (`refresh_catalog.py`, `search_catalog.py`, `fetch_dataset.py`, `report_to_pdf.py`, and the
  `mcp_smoke.py` smoke test) call by hand — so an agent's MCP call and a human's CLI reach the same
  answer, and the two never drift (**one source of truth**).
- **A Skill** — `.claude/skills/cambridge-open-data/SKILL.md`, the *cognitive* interface: the
  discover → fetch → cross-reference → infer playbook plus the gotchas that keep the agent's answers
  trustworthy.
- **Documentation** — `docs/` explaining how to install, configure, and use the Skill and the MCP
  server as complementary tools in your AI interaction with the Cambridge Open Data Portal.

## Install

[uv](https://docs.astral.sh/uv/) is the recommended runner. From a clone of this repo:

```bash
uv sync                      # install dependencies
uv run scripts/refresh_catalog.py        # pull the 280+ dataset index (seconds)
uv run scripts/mcp_smoke.py              # end-to-end check
```

The smoke test drives the live server and, with a populated cache, returns a report of tests. To do
this, three datasets need to be retrieved from the Portal, to create a catalog the smoke tests can run
against:

```bash
uv run scripts/fetch_dataset.py 9qm7-wbdc    # building permits — the coverage audit
uv run scripts/fetch_dataset.py ixg8-tyau    # salaries — the cross-dataset SQL
uv run scripts/fetch_dataset.py 5bn4-5wey    # operating budget — the wrong-name error
```

## Registering the MCP server

These are the commands to register the MCP server on the system where you run your AI agentic harness:

| Harness | Register |
| --- | --- |
| **opencode** (TUI / Desktop / Web) | `opencode mcp add cambridge-open-data-ma-ai -- uv run cambridge-open-data-ma-mcp` — writes `opencode.json` |
| **Claude Code** | `claude mcp add cambridge-open-data-ma-ai -- uv run cambridge-open-data-ma-mcp` |
| **Cursor** | `.cursor/mcp.json`: `{ "mcpServers": { "cambridge-open-data-ma-ai": { "command": "uv", "args": ["run", "cambridge-open-data-ma-mcp"] } } }` |
| **Cline / Roo** (VS Code) | add a stdio MCP server in settings: command `uv`, args `run cambridge-open-data-ma-mcp` |

The same stdio server registers with **Codex**, **Gemini CLI**, and **Antigravity** by a single
command each; **HTTP-only** clients (OpenWebUI, ChatGPT, Claude.ai) need a bridge because the
server is stdio-only. The [registration commands](docs/install.md#register-the-mcp-server)
give every harness's exact form, including the bridge.

The shareable registration is `opencode.json` at the repo root — that is OpenCode's own config, so
copy it in and the key `cambridge-open-data-ma-ai` is enough. The table above shows each *other*
harness's equivalent form; the server is a **stdio** FastMCP server, so the launch line is the same
for all of them and only the config shape differs.

## Installing the Skill

The Skill is the operational playbook for the discover → fetch → cross-reference → infer workflow.
It ships in two forms:

- **Canonical** — `.claude/skills/cambridge-open-data/SKILL.md`, read natively by **Claude Code**
  and **omp**. Drop the folder into the project or `~/.claude/skills/`. **Antigravity** also reads
  a `SKILL.md` natively (from `.agents/skills/` or `~/.gemini/config/skills/`).
- **Harness-agnostic mirror** — `skills/cambridge-open-data/SKILL.md`, the same body with the Claude
  / omp YAML frontmatter and self-audit step removed, ready to paste into any harness's rules or
  agent file (Cursor, Gemini CLI, and the rest).

Each harness's own delivery is tabulated in the [Deliver the Skill](docs/install.md#deliver-the-skill)
section of install.md.

## Worked use-cases (the `docs/` tutorials)

1. **Budget** — FY2027 salary vs. operating budget, cross-referenced by department
   (`ixg8-tyau` ⋈ `5bn4-5wey`).
2. **Parking tickets** — the recent-window trap: the portal cannot answer "tickets paid vs. issued,
   revenue lost" for the full history.
3. **Privately owned public spaces** — 28 spaces, 13 governing special permits, found by spatial
   discovery across the Open Space and PUD zoning layers.
4. **Property profile, 80 Thorndike St** — address + the building-permit *era gap* (current datasets
   start 2018-07).
5. **First Street Garage / East End House** — three distinct legal instruments; a headline finding that
   a childcare commitment was **never fulfilled** (existence is not delivery).
6. **Drive the Skill in opencode** — a harness how-to: the Skill running inside opencode against the
   live MCP server, end to end.

Items 1–5 are grounded analyses of real portal data; a few of them trace the author's own research,
so read the findings as that research and verify before relying on them. Item 6 shows how to drive
the whole workflow from a popular harness rather than by hand. See
[`docs/tutorials`](docs/tutorials/) for the full walkthroughs and the gotchas that make the answers
trustworthy.

## Configuration

Secrets and per-machine state live in `.env` — copy `.env.template` and fill in. The four
`CAM_OPEN_DATA_*` credentials are optional; two storage overrides
(`CAM_OPEN_DATA_CACHE_DIR`, `CAM_OPEN_DATA_REPORTS_DIR`) default to `<repo>/data` and
`<repo>/docs/reports`. The opencode key and the `cambridge://` resource namespace are not
environment variables — they are a client-side label, not a secret.

## Updating the docs

The website at <https://ali5ter.github.io/cambridge-open-data-ma-ai/> is built from `docs/`
using [VitePress](https://vitepress.dev); every push to `main` rebuilds and redeploys it automatically.

To change the site, edit the Markdown in `docs/` and push — or click the "Edit this page" link in a
page's footer to open its source file on GitHub. The link is a small footer element (a pencil icon and
text), present on every **documentation** page (Guide, Tutorials, Reference); VitePress omits the doc
footer on the homepage (`layout: home`) and the 404 page, so it is absent there. It is a *public*
hyperlink — every visitor sees it — and GitHub then gates the *action*: a contributor with write access
commits directly, everyone else is routed to "Fork and propose changes." The root `README.md` is the
GitHub project page, not part of the site build, so the two surfaces are edited independently.

## License

MIT — see [LICENSE](LICENSE).
