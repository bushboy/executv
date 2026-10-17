# ExecuTV — Developer Friction Logs & Product Feedback

> **Hackathon:** Build, Ship, Shape: Amazon Developer Hackathon 2026  
> **Project:** ExecuTV (AI Executive Workstation)  
> **Tracks Entered:** Alexa+ (Primary MCP Server), Fire TV (Secondary Lean-Back UI), Ring (Operational Signals)

Submitting documented friction logs provides direct product feedback to Amazon engineering teams and can earn up to a **10% bonus** on the total judging score.

---

## Executive Overview

This document logs developer experience (DX) friction encountered while building **ExecuTV** across the **Alexa+ MCP Streamable HTTP specification**, the **Fire TV / Vega OS Simulator environment**, and **Ring operational event feeds**. Each entry details the specific task attempted, observed behavior versus expectations, severity rating, applied workaround, and actionable suggestions for Amazon product teams.

Repo surfaces this log refers to:

| Track | ExecuTV surface |
| --- | --- |
| Alexa+ MCP | `apps/ingress_gateway` — Streamable HTTP at `POST/GET http://localhost:8000/mcp` (spec ≥ 2025-11-25) |
| Fire TV / Vega | `apps/visual_display_adapter` — 10-foot React/Vite UI at `http://localhost:5173` |
| Ring ingest | `POST http://localhost:8001/api/v1/events/ingest` → `operational_events` → Live Alerts |

---

## Friction Log Entry #1: Alexa+ MCP Server over Streamable HTTP

* **Tool / SDK:** Alexa+ MCP Integration (`mcp` Python SDK 2.x / Streamable HTTP spec `≥ 2025-11-25`)
* **Task Attempted:** Setting up a self-hosted Model Context Protocol (MCP) server running over Streamable HTTP transport with Server-Sent Events (SSE) telemetry for real-time tool inspection.
* **Steps Taken:**
  1. Initialized a Python `MCPServer` (`mcp.server.mcpserver`) and mounted `streamable_http_app(stateless_http=True, streamable_http_path="/")` on FastAPI at `/mcp`.
  2. Registered the six executive tools (`get_executive_brief`, `explain_metric_change`, `get_pending_decisions`, `execute_decision`, `start_workflow`, `get_recent_events`) and proxied them to `core_engine`.
  3. Configured a parallel SSE event stream at `GET /events/ticker` to broadcast live tool invocations to the Fire TV diagnostic ticker (MCP Streamable HTTP itself also uses SSE framing for streamed responses).
  4. Advertised protocol floor `2025-11-25` (SDK handshake `2025-11-25`, latest `2026-07-28`) on `GET /health`.
* **Expected Outcome:** Seamless HTTP connection handling with standard header negotiation, automatic `protocolVersion` selection at or above `2025-11-25`, and automatic tool parameter validation.
* **Actual Outcome:** Streamable HTTP specification requirements for chunked transfer encoding and session header persistence (`Mcp-Session-Id`) were strict. Local Inspector / simulation clients that omitted `Mcp-Session-Id` (or sent a bare `Host: localhost` without a port) dropped during multi-turn tool loops. SDK 2.x also moved transport knobs off the constructor onto `streamable_http_app()`, and default DNS-rebinding protection (`host=127.0.0.1`) rejected some in-process clients with `421 Invalid Host header`. FastMCP was renamed to `MCPServer` mid-scaffold (`mcp` 2.2), breaking v1 import paths.
* **Severity Rating:** **Medium**
* **Workaround Used:** Mounted Streamable HTTP with `stateless_http=True` and `host="0.0.0.0"` to disable auto DNS-rebinding on the sub-app; added FastAPI middleware that normalizes incoming `Mcp-Session-Id` (and falls back to a local simulation session id when the header is omitted); kept the TV ticker on a dedicated `/events/ticker` SSE so diagnostics do not depend on MCP session resume. Health JSON documents `spec_min`, transport, and the six-tool registry for reviewers.
* **Actionable Suggestion for Amazon Team:** Provide an official CLI validation tool or compliance test suite (e.g. `alexa-mcp-validator`) that runs automated verification against local Streamable HTTP endpoints before submission — covering `protocolVersion` ≥ 2025-11-25, `Mcp-Session-Id` persistence, Host-header allowlists, and `tools/list` schema checks.

---

## Friction Log Entry #2: Fire TV / Vega OS Simulator Visual Focus Sync

* **Tool / SDK:** Fire TV / Vega OS Web Simulator Environment
* **Task Attempted:** Rendering a 10-foot lean-back React web application synchronized with real-time audio narration highlights from the core engine.
* **Steps Taken:**
  1. Built a React/Vite dashboard configured for 1080p TV viewport rendering (`apps/visual_display_adapter`, TV-safe 5% inset, D-pad `:focus-visible` rings).
  2. Polled dual-payload updates from `GET /api/v1/briefings/current` and Live Alerts from `GET /api/v1/events`; subscribed to MCP tool telemetry via `EventSource` on `/events/ticker`.
  3. Implemented D-pad remote spatial navigation listeners (`keydown` arrow / Enter / Space on `FocusTile`).
* **Expected Outcome:** Smooth visual card scaling and focus highlighting when receiving synchronized highlight events from backend voice execution (`voice_summary` + visual cards).
* **Actual Outcome:** In the simulator / low-power TV profile, CSS transforms combined with polling + SSE redraws occasionally caused minor frame stutter. Spatial D-pad focus lost track when the briefing grid and Live Alerts rail re-rendered (new card ids) without explicitly re-focusing the primary DOM card. The simulator docs did not ship a standard React spatial-focus template for 10-foot web apps.
* **Severity Rating:** **Low**
* **Workaround Used:** Added `VoiceVisualFocusController` in the visual adapter to keep a stable focus index across payload refreshes, restore focus to the first tile after Live Alerts updates, and promote compositor layers with `transform: translateZ(0)`. Focusable tiles remain `tabIndex={0}` with visible focus rings (no hover-only interaction).
* **Actionable Suggestion for Amazon Team:** Expand the Fire TV / Vega simulator documentation to include standard React/React Native spatial focus templates and guidelines for handling real-time push events (SSE / WebSocket) without dropping D-pad focus.

---

## Friction Log Entry #3: Ring Hardware-Agnostic Operational Event Ingestion

* **Tool / SDK:** Ring Simulator / API Webhook Feeds
* **Task Attempted:** Ingesting real-time site alerts (e.g. warehouse delivery detection) into the executive briefing queue without requiring physical Ring hardware.
* **Steps Taken:**
  1. Designed an HTTP REST endpoint (`POST /api/v1/events/ingest`) on `core_engine`.
  2. Mapped incoming JSON alert payloads into normalized executive notification items (`operational_events` schema) and seeded Ring / delivery / dock examples.
  3. Tested event injection via cURL / Python and confirmed `get_recent_events` plus the Fire TV **Live Alerts** rail.
* **Expected Outcome:** Clean ingestion and instant rendering on both the Alexa+ voice query engine (`get_recent_events`) and Fire TV Live Alerts timeline.
* **Actual Outcome:** Testing event workflows without physical hardware required manually crafting mock JSON event payloads. Developer documentation lacked a standardized OpenAPI example set or web sandbox for generating sample Ring event triggers (security, access control, delivery).
* **Severity Rating:** **Low**
* **Workaround Used:** Created a standalone mock event generator (`scripts/seed_ring_events.py`) to emit structured Ring-style delivery and security payloads on demand against `POST /api/v1/events/ingest`. Seeded `operational_events` still load with `executv-seed` so the Live Alerts rail is demoable offline.
* **Actionable Suggestion for Amazon Team:** Provide a web-based Ring Event Simulator UI in the developer portal that allows developers to trigger mock security, access control, and delivery events directly to a webhook URL.

---

## Friction Log Entry #4: Bedrock Converse, SSE through an ALB, and demo reset

* **Tool / SDK:** Amazon Bedrock Converse API, Application Load Balancer idle timeout, MCP bearer gates
* **Task Attempted:** Move reasoning from Gemini to Bedrock without letting the model decide a $1.2M procurement, and keep the Fire TV stream alive for a judge session.
* **Steps Taken:**
  1. Put the risk tier in Python (`core_engine/policy.py`) and returned the CFO challenge before any model call.
  2. Called Bedrock only for audit-card wording, with an 8 second read timeout and the seeded card as the failure path.
  3. Set the ALB idle timeout to 120 seconds in `infra/alb.tf` and kept the 15 second SSE comment heartbeat.
  4. Added `POST /admin/reset-scenario` so one approval of the spot purchase does not stick for the next judge.
* **Expected Outcome:** A public MCP endpoint, a model that can narrate, and a screen that survives a proxy.
* **Actual Outcome:** The local stack can prove the gate and the five golden questions with `LLM_PROVIDER=seeded`. Standing the ECS services up still needs image URIs in ECR and `terraform apply` in `infra/`; that apply was not run from this workstation because it creates a NAT gateway, RDS, and a public load balancer.
* **Severity Rating:** **High** for schedule, **Medium** for the product surface.
* **Workaround Used:** Seeded fallback is the default. `scripts/demo_dry_run.py` runs the five questions twice on a throwaway SQLite seed. Video capture can fall back to the Docker Compose stack if the AWS apply slips past Oct 10.
* **Actionable Suggestion for Amazon Team:** Document a known-good ALB idle-timeout value for Streamable HTTP and SSE side-channels, and ship a one-command MCP Inspector check that asserts `protocol-version: 2025-11-25`, bearer rejection, and `tools/list` schema completeness against an ALB URL.

---

## Product Feedback Summary

| Product / Tool | Onboarding Experience | What Worked Well | What Needs Improvement | Would Build With Again? |
| :--- | :--- | :--- | :--- | :--- |
| **Alexa+ (MCP Spec)** | Excellent open standard framework. | Decoupled JSON-RPC tool schemas made agentic integration straightforward. Six-tool registry mapped cleanly onto an executive workstation. | Clearer documentation on Streamable HTTP session header requirements (`Mcp-Session-Id`), Host-header allowlists, and a pre-submit validator. | **Yes** — Highly flexible for enterprise agent systems. |
| **Fire TV / Vega Simulator** | Fast local setup via browser viewports. | Rendering standard React web apps on a 10-foot visual screen is low-friction. Dual payload (voice + visual) is a natural TV pattern. | Need out-of-the-box spatial focus libraries for React/JS apps and guidance for SSE-driven redraws. | **Yes** — Great for big-screen executive dashboards. |
| **Ring Event Ingestion** | Fully accessible via REST webhooks. | Simple data contract to normalize site/security alerts into business logic and a Live Alerts rail. | A built-in event mock sandbox in the developer portal would speed up hardware-free development. | **Yes** — Powerful for adding real-world operational signals. |

---

## Appendix — How we re-tested each entry

| Entry | Command / URL |
| --- | --- |
| #1 MCP | `GET http://localhost:8000/health` (transport + spec + tools); MCP endpoint `http://localhost:8000/mcp` |
| #2 Fire TV | `http://localhost:5173` — 10-foot brief + Live Alerts + D-pad focus |
| #3 Ring | `uv run python scripts/seed_ring_events.py` then `GET http://localhost:8001/api/v1/events` |
