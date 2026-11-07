# Configuration

The configuration surface is deliberately small. A principle drives it: **secrets and per-machine
state go in `.env`; a client-side label or resource namespace does not.** Copy `.env.template` to
`.env` and fill in what you need.

## Credentials (optional)

Public dataset reads and catalog search work with **no credentials at all**, just at a lower
anonymous rate limit. Add an app token to lift that limit:

| Variable | Purpose |
|---|---|
| `CAM_OPEN_DATA_APP_TOKEN_ID` | App token identifier. Sent as `X-App-Token` to lift the caller out of the anonymous throttling tier. |
| `CAM_OPEN_DATA_APP_TOKEN_SECRET` | App token secret. Unused for read calls; kept for completeness / future write access. |
| `CAM_OPEN_DATA_API_KEY_ID` | API key identifier, used as the HTTP Basic-auth username. Only needed for private/unlisted assets or write access. |
| `CAM_OPEN_DATA_API_KEY_SECRET` | API key secret, the HTTP Basic-auth password. Not currently needed. |

Get an app token at
<https://data.cambridgema.gov/profile/edit/developer_settings>.

## Storage (optional)

The two storage paths default to repo-relative locations and need no `.env`. Override them for a
shared/centralised cache, or when the package is *installed* rather than cloned (a `pip` user has no
repo `data/`):

| Variable | Default | Purpose |
|---|---|---|
| `CAM_OPEN_DATA_CACHE_DIR` | `<repo>/data` | Where the catalog and raw Parquet pulls live. |
| `CAM_OPEN_DATA_REPORTS_DIR` | `<repo>/docs/reports` | Where finished analysis reports live. |

Both are centralised in `cambridge_data.config.cache_dir()` and `reports_dir()`, and
`catalog.py`, `warehouse.py`, and `mcp.py` all resolve through them — so one env var moves every
entry point at once.

## What is *not* in `.env` (and why)

- **The opencode key** (`cambridge-open-data-ma-ai`) and the `cambridge://` resource namespace are
  a **client-side label**, not a secret or per-machine state. `opencode.json` is the shareable
  artifact users copy; env-ifying a label would be indirection for nothing.
- **`cambridge://`** is the resource namespace the server exposes; it is fixed by the server, not
  per-install.

## How `.env` is loaded

`cambridge_data.config` calls `load_dotenv(<repo>/.env)` at import time, so the four credentials and
the two storage overrides are read automatically whenever the library, a CLI, or the MCP server
starts. An env var already set in the shell takes precedence over the file (standard `python-dotenv`
behaviour), which is how a CI job or a published install points the cache at a different location
without editing the file.
