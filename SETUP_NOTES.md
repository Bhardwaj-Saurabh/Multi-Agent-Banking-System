# Setup Notes & Gotchas

Hard-won notes from getting this project running end-to-end (agent → Vertex AI → MCP Toolbox → Cloud SQL Auth Proxy → MySQL). Read this before a fresh setup — several dependency and version issues will otherwise block you.

## Running processes (three terminals)

1. **Cloud SQL Auth Proxy** → `127.0.0.1:3306`
   ```bash
   ./cloud-sql-proxy <PROJECT>:<REGION>:bank-sql --port 3306
   ```
2. **MCP Toolbox** (from `starter/`, env exported) → `127.0.0.1:5001`
   ```bash
   cd starter && export $(grep -v '^#' .env | xargs)
   ./toolbox --tools-file tools.yaml --port 5001
   ```
3. **ADK web server** (venv active, env exported) → `127.0.0.1:8000`
   ```bash
   cd starter && export $(grep -v '^#' .env | xargs)
   adk web --a2a
   ```

## Dependency version pins (critical)

The unbounded versions in the original `requirements.txt` resolve to broken combinations. Pinned versions that work together:

| Package | Pin | Why |
|---|---|---|
| `a2a-sdk` | `>=0.3.6,<0.4` | `google-adk` 2.3.0 imports `ClientEvent` from `a2a.client`, removed in a2a-sdk 1.x |
| `toolbox-core` | `==0.5.0` (`<1.0`) | Must match the `toolbox` server binary's MCP protocol (`2024-11-05`); 1.x drops it |
| `sse-starlette` | any | Required by a2a-sdk's HTTP server (`JSONRPCApplication`) for `adk web --a2a` |
| `toolbox` server binary | `0.5.0` | Keep client and server versions aligned |

## ADK 2.3.0 bug — `import json` (must patch)

`google-adk` 2.3.0 has a bug in `google/adk/cli/fast_api.py`: a redundant local `import json` inside the A2A-setup function makes `json` a local variable for the whole function, so an earlier `json.load()` raises `UnboundLocalError`. Symptom:

```
Failed to setup A2A agent <name>: cannot access local variable 'json' where it is not associated with a value
```

**This blocks all A2A agent registration.** Fix — remove the redundant local import (~line 749 of `fast_api.py` in the venv):

```python
    import inspect
    import json      # <-- delete this line
```

⚠️ This patch lives in the venv's site-packages, **not** in this repo. Recreating the venv re-introduces the bug — re-apply the fix, or upgrade to an ADK version where it's resolved.

## Database (Cloud SQL MySQL)

- DB name must be `bank-data` (matches `starter/tools.yaml`).
- Load schema/data from `starter/docs/deposit.sql` and `starter/docs/loan.sql`.
- MySQL 8 uses `caching_sha2_password`; when importing over the proxy with the `mysql` client, add `--get-server-public-key` (or connect over TLS).
- `.env` must set `MYSQL_PORT=3306` and `MYSQL_DATABASE=bank-data` — the toolbox 0.5.0 binary does **not** support the `${VAR:default}` fallback syntax, so `tools.yaml` uses plain `${VAR}` and the vars must be defined.

## Loan approval workflow

The loan sub-agents (`policy_agent`, `user_profile_agent`) use `output_schema`, and **ADK disables tool calls when `output_schema` is set** — so `load_artifacts` can never run and the GCS/PDF documents are never read. The policy criteria and customer profile are therefore embedded directly in the agent prompts (`starter/loan/loan.py`, `starter/loan/user-profile-base-prompt.txt`). The outstanding-balance prompt also rounds to whole dollars to avoid an `int`-schema truncation bug (`22183.29` → `2218329`).

## Testing evidence

Regenerate the result files with the full stack running:
```bash
export $(grep -v '^#' starter/.env | xargs)
python testing/bin/a2a.py --in testing/test_scenarios.csv --out testing/test_results
```
Produces `testing/test_results.{csv,json,txt}`.
