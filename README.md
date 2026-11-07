# cambridge-open-data-ma-ai

An **MCP server**, a **Skill**, and **tutorials** for asking an AI agent to discover, fetch,
cross-reference, and infer insights from the
[Cambridge MA Open Data Portal](https://data.cambridgema.gov) — a Socrata portal with 280+ public
datasets (budget, public safety, permitting, GIS/parcels, public health, schools, and more).

Ask a natural-language question about Cambridge civic data and get back a grounded answer built from
real cross-dataset analysis, not a single-table lookup. Public dataset reads and catalog search work
with **no credentials** at all.

## What is in the box

- **The server** — `cambridge_data.mcp`, exposed as the `cambridge-open-data-ma-mcp` console script,
  an 8-tool / 4-resource FastMCP (v1) server. It wraps the same library the CLIs call, so the harness
  and the CLI never drift (one source of truth).
- **The Skill** — `.claude/skills/cambridge-open-data/SKILL.md`, the operational playbook: the
  discover → fetch → cross-reference → infer workflow, plus the gotchas that stop a naive answer.
- **The tutorials** — `docs/`, five worked analyses that are also the test-suite of real use-cases
  (below), each reproducible from the repo's `Data provenance` section.

The server and the Skill are two views of one system — the *machine* interface (tools the agent can
call) and the *cognitive* interface (the *when/why* and the judgment the tools deliberately can't
encode). They version as a unit.

## Install

[uv](https://docs.astral.sh/uv/) is the recommended runner. From a clone of this repo:

```bash
uv sync                      # install dependencies
uv run scripts/refresh_catalog.py        # pull the 280+ dataset index (seconds)
uv run scripts/mcp_smoke.py              # end-to-end check
```

The smoke test drives the live server and, with a populated cache, reports **14/14**. It needs the
catalog plus the three raw datasets the coverage and cross-reference checks exercise:

```bash
uv run scripts/fetch_dataset.py 9qm7-wbdc    # building permits — the coverage audit
uv run scripts/fetch_dataset.py ixg8-tyau    # salaries — the cross-dataset SQL
uv run scripts/fetch_dataset.py 5bn4-5wey    # operating budget — the wrong-name error
```

On a fresh clone without that cache the cache-dependent checks **skip** (not fail) with a how-to
banner, and the run still exits 0 — a skip is not a failure. The cache is gitignored and rebuildable;
the `data/raw/*.parquet` files can also be copied from the `local-data-experiments` repo.

## Register the MCP server

The server is the universal part — any MCP-aware harness can use it. The commands below write the
server's config for that harness.

| Harness | Register |
| --- | --- |
| **opencode** (TUI / Desktop / Web) | `opencode mcp add cambridge-open-data-ma-ai -- uv run cambridge-open-data-ma-mcp` — writes `opencode.json` |
| **Claude Code** | `claude mcp add cambridge-open-data-ma-ai -- uv run cambridge-open-data-ma-mcp` |
| **Cursor** | `.cursor/mcp.json`: `{ "mcpServers": { "cambridge-open-data-ma-ai": { "command": "uv", "args": ["run", "cambridge-open-data-ma-mcp"] } } }` |
| **Cline / Roo** (VS Code) | add a stdio MCP server in settings: command `uv`, args `run cambridge-open-data-ma-mcp` |

The shareable registration is `opencode.json` at the repo root — copy it and the key is
`cambridge-open-data-ma-ai`.

## Deliver the Skill

The Skill is a `.claude/skills/` artifact, read natively by **Claude Code** and **omp** (drop the
`.claude/skills/cambridge-open-data/` folder into the project or `~/.claude/skills/`). For every
other harness the Skill is delivered by pasting `SKILL.md` into that harness's rules / agent /
instructions, because only those harnesses read the `.claude/skills/` contract. The server is the
part that works everywhere.

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

See [`docs/`](docs/) for the full tutorials and the gotchas that make the answers trustworthy.

## Configuration

Secrets and per-machine state live in `.env` — copy `.env.template` and fill in. The four
`CAM_OPEN_DATA_*` credentials are optional; two storage overrides
(`CAM_OPEN_DATA_CACHE_DIR`, `CAM_OPEN_DATA_REPORTS_DIR`) default to `<repo>/data` and
`<repo>/docs/reports`. The opencode key and the `cambridge://` resource namespace are not
environment variables — they are a client-side label, not a secret.

## Updating the docs

The website at <https://ali5ter.github.io/cambridge-open-data-ma-ai/> is built from `docs/`
by VitePress; every push to `main` rebuilds and redeploys it automatically, so there is no
manual "publish" step. To change the site, edit the Markdown in `docs/` and push — or click
"Edit this page" on any live page to open its source file on GitHub. The root `README.md`
is the GitHub project page, not part of the site build, so the two surfaces are edited
independently.

## License

MIT — see [LICENSE](LICENSE).
