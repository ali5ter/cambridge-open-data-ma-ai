# Install and register

The server is the universal part — any MCP-aware harness can use it. The commands below register
it for that harness; the Skill is a separate delivery (the last section).

> [!NOTE]
> The commands assume [uv](https://docs.astral.sh/uv/) is installed. The `uv run
> cambridge-open-data-ma-mcp` form runs the console script from *this repo's* virtualenv, so the
> working directory must be the repo (or a venv where the script is on `PATH`). A future published
> install (`pip install cambridge-open-data-ma-ai`) would put the script on `PATH` directly, so
> `command` would drop the `uv run` prefix. Verify a harness's exact flag syntax against its own
> docs — these drift between releases.

## Get the code

```bash
git clone https://github.com/ali5ter/cambridge-open-data-ma-ai
cd cambridge-open-data-ma-ai
uv sync                 # install dependencies into a local .venv
uv run scripts/refresh_catalog.py   # pull the dataset index (seconds)
```

Credentials are optional. Public dataset reads and catalog search work with no credentials, just at
a lower anonymous rate limit. To lift that limit, copy `.env.template` to `.env` and add an app
token from
<https://data.cambridgema.gov/profile/edit/developer_settings> — see
[Configuration](configuration.md).

## Register the MCP server

The registration is a small JSON block. `opencode.json` at the repo root is the shareable artifact
— copy it and edit the key, or let the CLI generate it.

### opencode (TUI, Desktop, Web)

opencode has a CLI that writes a project-level `opencode.json`:

```bash
opencode mcp add cambridge-open-data-ma-ai -- uv run cambridge-open-data-ma-mcp
```

The result (and the checked-in `opencode.json`) is:

```json
{
  "mcp": {
    "servers": {
      "cambridge-open-data-ma-ai": {
        "type": "local",
        "command": ["uv", "run", "cambridge-open-data-ma-mcp"]
      }
    }
  }
}
```

In the TUI, run `/mcp` to list registered servers and confirm `cambridge-open-data-ma-ai` is
connected.

### Claude Code

```bash
claude mcp add cambridge-open-data-ma-ai -- uv run cambridge-open-data-ma-mcp
```

### Cursor

Create `.cursor/mcp.json` at the project root:

```json
{
  "mcpServers": {
    "cambridge-open-data-ma-ai": {
      "command": "uv",
      "args": ["run", "cambridge-open-data-ma-mcp"]
    }
  }
}
```

### Cline / Roo (VS Code)

Add a stdio MCP server in the extension's settings — command `uv`, arguments
`run cambridge-open-data-ma-mcp` — or drop the equivalent into
`.roo/mcp.json` / `.cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "cambridge-open-data-ma-ai": {
      "command": "uv",
      "args": ["run", "cambridge-open-data-ma-mcp"]
    }
  }
}
```

### Codex

```bash
codex mcp add cambridge-open-data-ma-ai -- uv run cambridge-open-data-ma-mcp
```

Writes `[mcp_servers.cambridge-open-data-ma-ai]` to `~/.codex/config.toml`. Confirm with
`codex mcp list` (or `/mcp` in the TUI).

### Gemini CLI

```bash
gemini mcp add cambridge-open-data-ma-ai -- uv run cambridge-open-data-ma-mcp
```

Writes the server into `~/.gemini/settings.json` under `mcpServers`. Restart the CLI or run `/mcp`
to confirm.

### Antigravity

Antigravity reads a `mcpServers` block, not a CLI. Add it to `~/.gemini/config/mcp_config.json`
(global) or `.agents/mcp_config.json` (workspace) — or use the built-in MCP Store:

```json
{
  "mcpServers": {
    "cambridge-open-data-ma-ai": {
      "command": "uv",
      "args": ["run", "cambridge-open-data-ma-mcp"],
      "env": { "CAM_OPEN_DATA_CACHE_DIR": "/abs/path/to/repo/data" }
    }
  }
}
```

Antigravity does **not** interpolate shell variables, so write a literal path for
`CAM_OPEN_DATA_CACHE_DIR`. It also reads a `SKILL.md` natively, so the Skill can be delivered to it
without pasting (see below).

## Bridge to HTTP-only clients

**OpenWebUI**, **ChatGPT**, and **Claude.ai** accept MCP over HTTP only, so a stdio server like this
one will not connect to them directly. Two paths get you there.

### Local bridge — `mcpo` (OpenWebUI)

`mcpo` is an HTTP front-end for a stdio server. Start it, then point OpenWebUI at it:

```bash
uvx mcpo --host 0.0.0.0 --port 8000 -- uv run cambridge-open-data-ma-mcp
```

In OpenWebUI go to **Settings → Admin → Integrations → External Tool Servers** and add a server with
**Type = "MCP (Streamable HTTP)"** and URL `http://localhost:8000/mcp`. Registering MCP servers is
admin-only, and the bridge process must stay running for the duration.

### Remote endpoint — ChatGPT / Claude.ai

These call a remote URL (typically ending in `/sse` or `/mcp`); they do not run a local process.
Expose the server over HTTPS — tunnel it with `ngrok` or `cloudflared`, or host it — then, with
Developer Mode on (a paid-plan feature), add a custom connector pointing at that URL.

## Deliver the Skill

The Skill ships in two forms: the **canonical** copy at `.claude/skills/cambridge-open-data/SKILL.md`
(the Claude Code / omp form, with YAML frontmatter and a self-audit step), and a
**harness-agnostic mirror** at `skills/cambridge-open-data/SKILL.md` — the same body without that
frontmatter, ready to paste anywhere. The server alone works everywhere, but the gotchas (the part
that stops a wrong answer) live in the Skill.

| Harness | Register the server | Deliver the Skill |
|---|---|---|
| **opencode** | `opencode mcp add ...` → `opencode.json` | custom agent, or paste `SKILL.md` into the README/agent instructions |
| **Claude Code** | `claude mcp add ...` | drop `.claude/skills/cambridge-open-data/` into the project or `~/.claude/skills/` |
| **Antigravity** | `mcpServers` in `mcp_config.json` | native — reads `SKILL.md`; drop the mirror into `.agents/skills/` |
| **Codex / Gemini CLI / others** | `codex mcp add ...` / `gemini mcp add ...` / config | paste the mirror's body into the harness's rules/agent file |
| **Cursor** | `.cursor/mcp.json` | `.cursor/rules`, or paste `SKILL.md` |
| **Cline / Roo** | settings / `.roo/mcp.json` | rules file, or paste `SKILL.md` |

## Verify

After registering, from the repo:

```bash
uv run scripts/mcp_smoke.py      # drives the live server over stdio
uv run ruff check .              # lint the package
```

The smoke test talks to the server exactly as a harness would (over stdio) and confirms each tool
and resource works end-to-end, including the JSON-serialisation boundary that trips up a naive
MCP wrapper.

It needs the local cache — the catalog plus the three raw datasets the coverage and cross-reference
checks exercise — so a full run reports **14/14**:

```bash
uv run scripts/refresh_catalog.py        # the catalog (if not already pulled)
uv run scripts/fetch_dataset.py 9qm7-wbdc    # building permits — the coverage audit
uv run scripts/fetch_dataset.py ixg8-tyau    # salaries — the cross-dataset SQL
uv run scripts/fetch_dataset.py 5bn4-5wey    # operating budget — the wrong-name error
```

On a fresh clone without that cache the cache-dependent checks **skip** (not fail) with a how-to
banner, and the run still exits 0 — a skip is not a failure. The cache is gitignored and rebuildable,
and the `data/raw/*.parquet` files can also be copied from the `local-data-experiments` repo.
