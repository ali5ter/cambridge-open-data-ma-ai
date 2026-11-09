# Install and register

This page provides guidance for the registration of the MCP Server and installation of the Skill provided by this project.

## Prerequisites

Some commands in this page assume [uv](https://docs.astral.sh/uv/) is installed. This provides a convenient Python environment so that the scripts work from the local git repo.

```bash
git clone https://github.com/ali5ter/cambridge-open-data-ma-ai
cd cambridge-open-data-ma-ai
uv sync                 # install dependencies into a local .venv
mkdir -p ~/.local/bin && ln -sf "$PWD/scripts/cambridge-data" ~/.local/bin/cambridge-data
cambridge-data refresh   # pull the dataset index (seconds)
```

The `ln -sf` line puts the `cambridge-data` CLI on your `PATH` (add `~/.local/bin` to it if it
isn't already), so the bare command runs from any directory instead of `uv run scripts/…`.

Credentials are optional. Public dataset reads and catalog search work with no credentials, just at
a lower anonymous rate limit. To lift that limit, copy `.env.template` to `.env` and add an app
token from <https://data.cambridgema.gov/profile/edit/developer_settings>. Read more in
[Configuration](configuration.md).

## Registering the MCP server

::: note MCP?
MCP (Model Context Protocol) is a common way to connect AI assistants to your other apps, roughly like USB-C is for cables. Before it, every AI tool needed its own custom link to every program you wanted it to talk to; MCP lets one AI reach your files, calendar, or any other service the same way, and a tool you build once can work with any AI. Anthropic made it free for anyone to use in late 2024, and it has become the go-to way to wire AI into the rest of your digital life.
:::

The registration is defined using a small JSON block that is inserted into an AI harness configuration. Some harnesses also perform registration through their own CLI.

An example of this JSON block can be seen in the `opencode.json` file.

### OpenCode (TUI, Desktop, Web)

The `opencode.json` files in this project will register the MCP server for this project as soon as you run the OpenCode MCP.

[OpenCode](https://opencode.ai) has a CLI that can also write the openCode global level configuration:

```bash
opencode mcp add --global cambridge-open-data-ma-ai -- uv run cambridge-open-data-ma-mcp
```

In the OpenCode TUI, run `/mcp` to list registered servers and confirm `cambridge-open-data-ma-ai` is connected.

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

## HTTP-only connection to the MCP Server

The GUI based agentic harnesses typically connect to MCP Servers using HTTP.

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

## Installing the Skill

The Skill ships in two forms. The difference is YAML frontmatter, the
[Agent Skills](https://agentskills.io) contract that a native reader needs to
*discover* and *advertise* a skill:

- **Canonical** — `.claude/skills/cambridge-open-data/SKILL.md`, with the `name`
  and `description` frontmatter. This is the drop-in for the native readers —
  OpenCode, Claude Code, Antigravity, and Gemini CLI. It already lives in this
  repo, so OpenCode and Claude Code pick it up the moment they open it; for the
  others, copy it into the harness's skills directory (table below).
- **Mirror** — `skills/cambridge-open-data/SKILL.md`, the same body with the
  frontmatter removed, for harnesses that ingest a rules or agent file rather
  than parse the skill contract (Cursor, Cline / Roo, Codex, and the like).

::: warning The mirror is body-only
A body-only skill has no `description`, and OpenCode advertises a skill only when
it has one — so the mirror does **not** auto-discover in OpenCode. Use the
canonical form there: OpenCode reads `.claude/skills` as a project source, or
copy it to `.opencode/skills/<id>/SKILL.md`.
:::

| Harness | Register the server | Install the Skill |
|---|---|---|
| **[OpenCode](https://opencode.ai/docs/skills/)** | `opencode mcp add ...` → `opencode.json` | canonical — read from `.claude/skills` in-repo; else copy to `.opencode/skills/<id>/` (project) or `~/.config/opencode/skills/<id>/` (global) |
| **[Claude Code](https://code.claude.com/docs/en/skills)** | `claude mcp add ...` | canonical — read from `.claude/skills` in-repo; else copy to `.claude/skills/` (project) or `~/.claude/skills/` (personal) |
| **[Antigravity](https://antigravity.google/docs/skills/)** | `mcpServers` in `mcp_config.json` | canonical — copy to `.agents/skills/` (workspace) or `~/.gemini/config/skills/` (global) |
| **[Gemini CLI](https://geminicli.com/docs/cli/skills/)** | `gemini mcp add ...` | canonical — copy to `.gemini/skills/` or the `.agents/skills/` alias, or `gemini skills install <path>` |
| **[Cursor](https://cursor.com/docs/rules)** | `.cursor/mcp.json` | mirror — paste the body into a `.cursor/rules/*.mdc` rule, or drop an `AGENTS.md` at the project root |
| **[Cline / Roo](https://docs.cline.bot/customization/cline-rules)** | settings / `.roo/mcp.json` | mirror — paste the body into a `.clinerules/` (or `.cline/rules/`) file, or an `AGENTS.md` at the project root |
| **Codex (OpenAI)** | `codex mcp add ...` | mirror — paste the body into an `AGENTS.md` at the project root ([AGENTS.md](https://agents.md/)) |

## Verify the installation

You can run the smoke test which talks to the MCP server exactly as a harness would and confirms each tool and resource works end-to-end.

The catalog plus and three datasets are used in the testing. Use these commands to set these up:

```bash
cambridge-data refresh                  # the catalog (if not already pulled)
cambridge-data fetch 9qm7-wbdc          # building permits — the coverage audit
cambridge-data fetch ixg8-tyau          # salaries — the cross-dataset SQL
cambridge-data fetch 5bn4-5wey          # operating budget — the wrong-name error
```

Then run the smoke test to see if 14 out of 14 tests pass:

```bash
uv run scripts/mcp_smoke.py
```
