# ExecuTV

AI executive workstation for **Fire TV** and **Alexa+ MCP**.

A spoken Alexa+ request produces two outputs at once: a concise `voice_summary` for Alexa, and a 10-foot visual briefing on the Fire TV in the room. The ingress layer speaks the Model Context Protocol over **Streamable HTTP** (spec **2025-11-25**) so Alexa+ can call tools. Amazon Bedrock Converse is the primary reasoner, with a seeded fallback when Bedrock is off or times out. Spoken numbers come from the AcroCorp seed data.

Licensed under the [MIT License](LICENSE).

## Repository map

```
apps/ingress_gateway/          FastAPI + MCP Streamable HTTP server and SSE tool ticker
apps/core_engine/              FastAPI orchestration API, Bedrock reasoner, dual-payload formatter
apps/visual_display_adapter/   React/Vite 10-foot Fire TV UI (brief and Live Alerts)
packages/core_data_layer/      SQLModel models, PostgreSQL repositories, seed scripts
docs/                          Architecture and design notes
infra/                         ECS Fargate, ALB, RDS, Secrets Manager, S3 + CloudFront
LICENSE                        MIT
```

| Path | Runtime | Role |
| --- | --- | --- |
| `packages/core_data_layer` | Python 3.12 | Shared PostgreSQL models and access |
| `apps/core_engine` | FastAPI `:8001` | Orchestration, Bedrock or seeded reasoning, event ingest, dual payloads |
| `apps/ingress_gateway` | FastAPI `:8000` | Alexa+ MCP (`/mcp`) and SSE ticker (`/events/ticker`) |
| `apps/visual_display_adapter` | nginx `:5173` | 10-foot TV UI |

Python packages are a **uv workspace** (root `pyproject.toml`) with a pip-compatible `requirements.txt`.

## MCP tools

Transport: **Streamable HTTP** at `http://localhost:8000/mcp`. The SDK handshake includes **2025-11-25**; the latest supported protocol version is **2026-07-28**.

| Tool | Purpose |
| --- | --- |
| `get_executive_brief` | Morning brief (voice + Fire TV cards) |
| `explain_metric_change` | KPI delta explanation |
| `get_pending_decisions` | Open go/no-go items |
| `execute_decision` | Approve or reject a decision |
| `start_workflow` | Kick off incident or board-pack workflows |
| `get_workflow_status` | Status of RFQ #12345 or the blocked Q3 close |
| `get_recent_events` | Ring camera events, including Gate 4 |
| `register_display_pairing` | Bind a session to a Fire TV pairing code |

`POST /mcp` requires `Authorization: Bearer <MCP_BEARER_TOKEN>`, `protocol-version: 2025-11-25`, and `mcp-session-id` on tool calls. `POST /mcp/v1/tools/call` is a local helper and is not part of the Streamable HTTP surface.

Ring ingest: `POST http://localhost:8001/api/v1/events/ingest`. Utterances: `POST http://localhost:8001/api/v1/reason` (Bedrock when `LLM_PROVIDER=bedrock`, otherwise seeded). Restore the demo with `POST /admin/reset-scenario` and the same bearer token.

## Quick start

Prerequisites: **Docker**, and a **local PostgreSQL** on port **5432**. This repo does not run a database container.

1. Copy `.env.example` to `.env`. Docker defaults use `host.docker.internal` for Postgres.

   ```bash
   cp .env.example .env
   ```

   PowerShell: `Copy-Item .env.example .env`

   Create the database and login if they do not exist:

   ```sql
   CREATE USER executv WITH LOGIN PASSWORD 'executv';
   CREATE DATABASE executv OWNER executv;
   ```

2. Build and start the stack (seed job, core engine `:8001`, ingress `:8000`, Fire TV UI `:5173`):

   ```bash
   docker compose up --build -d
   ```

   The `seed` service runs `executv-seed` against host Postgres, then exits.

Host-only Python and Node workflow: `uv sync --all-packages`, set `POSTGRES_HOST=127.0.0.1` in `.env`, then `uv run executv-core-engine`, `uv run executv-ingress`, and `npm run dev` in `apps/visual_display_adapter`.

### Check the stack

- `GET http://localhost:8000/health` — Streamable HTTP metadata and the tool list
- `GET http://localhost:8001/api/v1/briefings/current` — dual payload (`voice_summary` + visual)
- `POST http://localhost:8001/api/v1/events/ingest` — Gate 4 Ring freight event (`uv run python scripts/seed_ring_events.py`)
- `GET http://localhost:8001/api/v1/events` — Live Alerts data
- `POST http://localhost:8001/api/v1/reason` — Bedrock or seeded intent to tool arguments
- `POST http://localhost:8000/admin/reset-scenario` — bearer token restores the AcroCorp seed
- `http://localhost:5173` — 10-foot UI with Live Alerts

OpenAPI: Swagger UI at `http://localhost:8001/docs` (spec `http://localhost:8001/openapi.json`, checked-in copy [`docs/openapi/core-engine.json`](docs/openapi/core-engine.json)). Ingress docs: `http://localhost:8000/docs`.

Further reading: [docs/architecture.md](docs/architecture.md), [docs/friction-log.md](docs/friction-log.md).
