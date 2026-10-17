# ExecuTV

AI Executive Workstation for **Fire TV** and **Alexa+ MCP**.

ExecuTV turns a spoken Alexa+ request into two coordinated outputs at once: a concise `voice_summary` for Alexa, and a 10-foot visual briefing for the Fire TV in the room. The ingress layer speaks the Model Context Protocol over **Streamable HTTP** (spec **2025-11-25**) so Alexa+ can call tools. Amazon Bedrock Converse is the primary reasoner, with a seeded fallback when Bedrock is off or times out. Every spoken number comes from the AcroCorp seed.

License: [MIT](LICENSE) (Open Source Mini Challenge).

## Repository map

```
apps/ingress_gateway/          FastAPI + MCP Streamable HTTP server & SSE tool ticker
apps/core_engine/              FastAPI orchestration API, Bedrock reasoner, Dual-Payload Formatter
apps/visual_display_adapter/   React/Vite 10-foot Fire TV UI (brief + Live Alerts)
packages/core_data_layer/      SQLModel models, PostgreSQL repositories, seed scripts
docs/                          Architecture, friction log, product feedback
LICENSE                        MIT
```

| Path | Runtime | Role |
| --- | --- | --- |
| `packages/core_data_layer` | Python 3.12 | Shared PostgreSQL models and access |
| `apps/core_engine` | FastAPI `:8001` | Orchestration, Bedrock or seeded reasoning, event ingest, dual payloads |
| `apps/ingress_gateway` | FastAPI `:8000` | Alexa+ MCP (`/mcp`) and SSE ticker (`/events/ticker`) |
| `apps/visual_display_adapter` | nginx `:5173` | 10-foot TV UI |

Python packages are a **uv workspace** (root `pyproject.toml`) with a pip-compatible `requirements.txt`. Follow [BUILD.md](BUILD.md) for the incremental implementation order.

## MCP tool suite (Alexa+ track)

Transport: **Streamable HTTP** at `http://localhost:8000/mcp`. SDK handshake includes **2025-11-25**; latest supported is **2026-07-28**.

| Tool | Purpose |
| --- | --- |
| `get_executive_brief` | Morning brief (voice + Fire TV cards) |
| `explain_metric_change` | KPI delta explanation |
| `get_pending_decisions` | Open go/no-go items |
| `execute_decision` | Approve or reject a decision |
| `start_workflow` | Kick off incident / board-pack workflows |
| `get_workflow_status` | Status of RFQ #12345 or the blocked Q3 close |
| `get_recent_events` | Ring camera events, including Gate 4 |
| `register_display_pairing` | Bind a session to a Fire TV pairing code |

`POST /mcp` requires `Authorization: Bearer <MCP_BEARER_TOKEN>`, `protocol-version: 2025-11-25`, and `mcp-session-id` on tool calls. `POST /mcp/v1/tools/call` is a local helper and is not part of the Streamable HTTP compliance claim.

Ring ingest: `POST http://localhost:8001/api/v1/events/ingest`. Utterances: `POST http://localhost:8001/api/v1/reason` (Bedrock when `LLM_PROVIDER=bedrock`, otherwise seeded). Restore the demo with `POST /admin/reset-scenario` and the same bearer token.

## Hackathon reviewer quick start

Prerequisites: **Docker**, plus a **local PostgreSQL** on port **5432** (this repo does not run a database container).

1. Copy `.env.example` to `.env` (Docker defaults use `host.docker.internal` for Postgres).

   ```bash
   cp .env.example .env
   ```

   PowerShell: `Copy-Item .env.example .env`

   Create a database and login if they do not exist:

   ```sql
   CREATE USER executv WITH LOGIN PASSWORD 'executv';
   CREATE DATABASE executv OWNER executv;
   ```

2. Build and start the stack (seed job, core engine `:8001`, ingress `:8000`, Fire TV UI `:5173`):

   ```bash
   docker compose up --build -d
   ```

   The `seed` service runs `executv-seed` against host Postgres, then exits.

Host-only Python/Node workflow (optional): `uv sync --all-packages`, point `POSTGRES_HOST=127.0.0.1` in `.env`, then `uv run executv-core-engine` / `uv run executv-ingress` / `npm run dev` in `apps/visual_display_adapter`.

### What to inspect

- `GET http://localhost:8000/health` — Streamable HTTP metadata + the 6 tools
- `GET http://localhost:8001/api/v1/briefings/current` — dual payload (`voice_summary` + visual)
- `POST http://localhost:8001/api/v1/events/ingest` — Gate 4 Ring freight event (`uv run python scripts/seed_ring_events.py`)
- `GET http://localhost:8001/api/v1/events` — Live Alerts data
- `POST http://localhost:8001/api/v1/reason` — Bedrock or seeded intent → tool args
- `POST http://localhost:8000/admin/reset-scenario` — bearer token restores the AcroCorp seed
- `infra/` — ECS Fargate, ALB idle timeout 120s, RDS, Secrets Manager, S3 + CloudFront
- `http://localhost:5173` — 10-foot UI with **Live Alerts**

OpenAPI: Swagger UI at `http://localhost:8001/docs` (spec `http://localhost:8001/openapi.json`, checked-in copy [`docs/openapi/core-engine.json`](docs/openapi/core-engine.json)). Ingress: `http://localhost:8000/docs`. Judging notes: [docs/friction-log.md](docs/friction-log.md), [docs/product-feedback.md](docs/product-feedback.md).

## Private-repo collaborators (Devpost)

This repository is private. Invite **pull** access for Devpost testing and Amazon DevRel **before** submission:

| Invite | GitHub |
| --- | --- |
| `testing@devpost.com` | Devpost tester (email invite) |
| chris-trag | [github.com/chris-trag](https://github.com/chris-trag) |
| knmeiss | [github.com/knmeiss](https://github.com/knmeiss) |
| giolaq | [github.com/giolaq](https://github.com/giolaq) |
| anishamalde | [github.com/anishamalde](https://github.com/anishamalde) |
| mosesroth | [github.com/mosesroth](https://github.com/mosesroth) |
| emersonsklar | [github.com/emersonsklar](https://github.com/emersonsklar) |

```bash
gh api -X POST "repos/OWNER/REPO/invitations" -f email="testing@devpost.com" -f permission="pull"
for user in chris-trag knmeiss giolaq anishamalde mosesroth emersonsklar; do
  gh api -X PUT "repos/OWNER/REPO/collaborators/${user}" -f permission="pull"
done
```
