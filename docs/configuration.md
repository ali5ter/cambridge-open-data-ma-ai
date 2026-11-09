# Configuration

The configuration for this project is deliberately small. You override the default settings using specific variables are defined in a `.env` file. If you want to do this, you need to copy the template provided to create a configuration file and edit it for your needs:

```bash
cd cambridge-open-data-ma-ai
cp .env.template .env
$EDITOR .env
```

## Credentials (optional)

Public dataset reads and catalog search work with **no credentials at all**, just at a lower
anonymous rate limit.

If you already have a [Cambridge MA Open Data Portal](https://data.cambridgema.gov) app token to lift those limits, then you can define those in the `.env` file.

These are the variables to define:

| Variable | Purpose |
|---|---|
| `CAM_OPEN_DATA_APP_TOKEN_ID` | App token identifier. Sent as `X-App-Token` to lift the caller out of the anonymous throttling tier. |
| `CAM_OPEN_DATA_APP_TOKEN_SECRET` | App token secret. Unused for read calls; kept for completeness / future write access. |
| `CAM_OPEN_DATA_API_KEY_ID` | API key identifier, used as the HTTP Basic-auth username. Only needed for private/unlisted assets or write access. |
| `CAM_OPEN_DATA_API_KEY_SECRET` | API key secret, the HTTP Basic-auth password. Not currently needed. |

You can get an app token at
<https://data.cambridgema.gov/profile/edit/developer_settings>.

## Storage (optional)

There are two storage paths that default to repo-relative locations and need no definition in the `.env` file.

If you want to override them, use these variables:

| Variable | Default | Purpose |
|---|---|---|
| `CAM_OPEN_DATA_CACHE_DIR` | `<repo>/data` | Where the catalog and raw Parquet pulls live. |
| `CAM_OPEN_DATA_REPORTS_DIR` | `<repo>/docs/reports` | Where finished analysis reports live. |
