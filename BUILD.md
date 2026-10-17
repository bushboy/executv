# ExecuTV build order

Implement the workstation in four increments. Each step should be runnable before the next one starts. Do not skip ahead: later apps assume the previous contract exists.

## 1. `packages/core_data_layer`

**Done when:** PostgreSQL is up, tables exist, and `executv-seed` wipes and loads Region B margin at 18.3%, the pending $1.2M and $450k decisions, RFQ #12345, and the Gate 4 Ring freight backlog.

- Define SQLModel entities (`KPI`, `MetricDriver`, `DecisionItem`, `DecisionAuditLog`, `WorkflowInstance`, `WorkflowStep`, `OperationalEvent`).
- Expose a PostgreSQL engine and `get_session()` generator.
- Add repositories for briefings, decisions, workflows, and operational events.
- Expose sync + async SQLAlchemy engines and a FastAPI-friendly session generator.
- Add repositories for executives, sessions, briefings, dual payloads, and tool events.
- Ship a seed script that is idempotent on re-run.

```bash
docker compose up -d
uv run executv-seed
```

## 2. `apps/core_engine`

**Done when:** `GET /v1/briefings/current` and `POST /v1/orchestrate` return a dual payload — Alexa `voice.speech` / `voice.ssml` plus a Fire TV `visual` document.

- Depend on `core-data-layer` for context load and persistence.
- Implement the Dual-Payload Formatter as a pure mapping from briefing/agenda → `DualPayload` (`voice_summary` + visual).
- Expose orchestration HTTP (`/v1` and `/api/v1`), Bedrock or seeded `POST /api/v1/reason`, and Ring ingest `POST /api/v1/events/ingest`.
- Keep CORS open for the Vite TV client on `:5173`.

```bash
uv run executv-core-engine
# http://localhost:8001/docs
```

## 3. `apps/ingress_gateway`

**Done when:** Alexa+ can call MCP tools over Streamable HTTP, and the TV client can subscribe to tool activity on SSE.

- Mount MCP Python SDK 2.x `MCPServer` Streamable HTTP at `/mcp` (stateless HTTP, spec ≥ 2025-11-25).
- Register the six executive tools: `get_executive_brief`, `explain_metric_change`, `get_pending_decisions`, `execute_decision`, `start_workflow`, `get_recent_events`.
- Publish every tool start/complete/error on `GET /events/ticker`.
- Do not put SQL in this app; the engine owns persistence.

```bash
uv run executv-ingress
# MCP:  http://localhost:8000/mcp
# SSE:  http://localhost:8000/events/ticker
```

## 4. `apps/visual_display_adapter`

**Done when:** a 1920×1080-class Fire TV surface renders the visual half of the dual payload and a live ticker, with D-pad focus (no hover-only interaction).

- Vite + React client with TV-safe inset (`5vh` / `5vw`).
- Large type, high-contrast executive theme, visible focus rings.
- Poll `core_engine` for the current briefing and `/api/v1/events` for the **Live Alerts** rail; subscribe to ingress SSE for the ticker.
- Show a loading state until the engine returns the AcroCorp briefing. The screen does not invent revenue or margin figures.

```bash
cd apps/visual_display_adapter
npm install
npm run dev
# http://localhost:5173
```
