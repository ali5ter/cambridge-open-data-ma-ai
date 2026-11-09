# Tutorial 6 — Drive the Skill in opencode

> **Question.** "Which Cambridge departments spent the most on salaries in the FY2027 budget, and how
> does that line up with their operating budget?"

Tutorials 1–5 are the *answers* this toolkit produces. This one is the *how* — the same question, but
driven from a popular harness ([opencode](https://opencode.ai)) so the MCP server does the work and
the Skill's gotchas stop it from returning a wrong one. You end with a grounded, cross-dataset answer
and a record of every tool call the agent made to reach it.

## 1. Register the server

From the repo root:

```bash
opencode mcp add cambridge-open-data-ma-ai -- uv run cambridge-open-data-ma-mcp
```

That writes `opencode.json` at the repo root with one entry under `mcp.servers`. Start opencode in this
directory and run `/mcp` to confirm `cambridge-open-data-ma-ai` is connected and its eight tools are
listed. The server is stdio, so opencode launches it for you. See [install.md](../install.md) for the
other harnesses and the HTTP bridge for OpenWebUI, ChatGPT, and Claude.ai.

## 2. Give the agent the Skill

The server alone works everywhere, but the gotchas — the part that stops a *wrong* answer — live in the
Skill. For opencode, deliver it one of two ways:

- **Custom agent** — point opencode at a small agent file that loads `SKILL.md` (see
  [install.md → Installing the Skill](../install.md#installing-the-skill)).
- **Inline** — paste the body of `.claude/skills/cambridge-open-data/SKILL.md` into your `README.md` or
  agent instructions; opencode reads it as project context.

With both in place the agent knows *both* the tools and the rules for using them safely.

## 3. Ask the question and watch the tool calls

Ask opencode the question in plain English:

> "Which Cambridge departments spent the most on salaries in the FY2027 budget, and how does that line
> up with their operating budget?"

A grounded run makes this sequence of MCP tool calls, each on its own:

- `refresh_catalog` — pull the dataset index (a few seconds) if the local cache is missing.
- `search_datasets("budget salaries")` — discover `ixg8-tyau` (Budget – Salaries) and read its
  `columns_field_name`; then `search_datasets("operating expenditure")` for `5bn4-5wey`
  (Budget – Operating Expenditures).
- `fetch_dataset` for both ids — caches each as Parquet.
- `query` — the cross-dataset join, returning JSON-native rows rather than numpy types.
- `coverage_audit` / `field_coverage` — before trusting the total, confirm the fields it aggregates over
  are actually populated (the recent-window trap).

The join itself is:

```sql
SELECT s.department,
       COUNT(*)  AS positions,
       ROUND(SUM(TRY_CAST(s.total_salary AS DOUBLE))) AS salary
FROM ds_ixg8_tyau AS s
GROUP BY 1
ORDER BY 3 DESC
LIMIT 3
```

For FY2027 both budget datasets are fully populated, so the join is clean — but the *habit* of running
the coverage check is what generalises to a dataset that isn't.

**The same loop, by hand.** Each tool call above is one `cambridge-data` subcommand —
`refresh_catalog` → `refresh`, `search_datasets` → `search`, `fetch_dataset` → `fetch`, `query` →
`query`, `coverage_audit` → `audit` — so the agent's sequence is also a shell session:

```bash
cambridge-data refresh
cambridge-data search "budget salaries"
cambridge-data search "operating expenditure"
cambridge-data fetch ixg8-tyau
cambridge-data fetch 5bn4-5wey
cambridge-data audit ixg8-tyau        # the coverage guard, by hand
cambridge-data query "SELECT s.department, COUNT(*) positions,
    ROUND(SUM(TRY_CAST(s.total_salary AS DOUBLE))) salary
  FROM ds_ixg8_tyau s GROUP BY 1 ORDER BY 3 DESC LIMIT 3"
```

That is the point of sharing one library: the harness's `refresh_catalog → search_datasets →
fetch_dataset → query → coverage_audit` and this shell session are the same calls over
`cambridge_data`, so they cannot drift.

## 4. The answer

The agent answers in chat (the default output mode) with the top salary departments and their operating
spend side by side — and, because the Skill ran the coverage check, it can say the numbers are
trustworthy for this fiscal year rather than merely present. Tutorials 1 and 5 show the same *answers*
in full; this one shows the *loop* that produces them.

## What this tutorial demonstrates

- The MCP server doing the work — `refresh_catalog → search_datasets → fetch_dataset → query →
  coverage_audit` — driven from a harness rather than typed by hand.
- Delivering the Skill to a harness so the gotchas run *for* the agent, not just for you.
- **By hand, too.** The same sequence is five `cambridge-data` subcommands, so the agent path and the
  shell path are one call set.
- Why "one source of truth" matters: the harness, the CLI, and ad-hoc Python all reach the same answer
  because they share `cambridge_data`.

For the other harnesses (Claude Code, Cursor, Cline/Roo, Codex, Gemini CLI, Antigravity) and the HTTP
bridge, see [install.md](../install.md).
