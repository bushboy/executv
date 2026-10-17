# ExecuTV Architecture Spec v3
**Date:** October 7, 2026  
**Status:** Production-Ready Baseline for Coding Agents  
**Target Code Freeze:** October 17, 2026  

---

## 1. Executive Summary & Version 3 Delta

ExecuTV is a voice-first executive workstation bringing enterprise intelligence to the living room via Fire TV, Alexa+ MCP over Streamable HTTP, and real-time speech processing (AssemblyAI). 

Version 3 (v3) updates Version 2 (v2) into an unambiguous, production-grade specification ready for immediate code execution before the **October 17, 2026 code freeze**. All open items from v2 have been resolved, contracts strictly aligned, and the CRIT Strategic Reasoning framework integrated into the in-process `core_engine`.

### Key Changes in Version 3
1. **Resolved $1.2M Decision Impact:** Quantified trade-offs ($1.2M spot purchase recovers +1.5% margin in Region B to 19.8% and prevents $3.5M Plant 3 downtime; declining saves $1.2M cash but causes immediate $3.5M revenue loss).
2. **Code-Enforced CRIT Risk Tiers:** Explicit deterministic policy logic enforcing 0-turn auto-approvals (Low), 0-turn on-screen warnings (Medium), and 1-turn CRIT challenge questions (High).
3. **AWS Bedrock Integration:** Locked `anthropic.claude-3-5-sonnet-20241022-v2:0` in `us-east-1` via the Bedrock Converse API with 3.0s deterministic template fallbacks.
4. **Causal AcroCorp Storyline:** Fully linked 5-step causal chain connecting Supplier X, Gate 4 logistics rerouting, Q3 Month-End Close audit block, Ring Gate 4 camera feed, and the $1.2M procurement decision.
5. **Contract & Schema Alignment:** Standardized Pydantic models across REST and MCP (`DualPayload`, `VisualPayload`, `VisualCard`, `highlighted_card_id`, `session_id`, `critical` severity enum, and `audit` UI layout).
6. **AWS ECS + SSE Resilience:** ECS Fargate topology behind ALB with 300s idle timeout, 15s SSE heartbeats, S3+CloudFront Fire TV hosting, and `POST /admin/reset-scenario` demo protection.

---

## 2. System Topology & Data Flow

All incoming user requests flow through `ingress_gateway` (Port `8000` for Alexa+ MCP / REST) or `ingress_gateway_assemblyai` (Port `8002` for WebSocket STT). The unified `core_engine` (Port `8001`) houses orchestration, policy enforcement, CRIT reasoning, and publishes real-time UI state updates over Server-Sent Events (SSE).

```
                      ┌────────────────────────────────────────┐
                      │    Co-Equal Voice Input Gateways       │
                      │                                        │
                      │  ┌──────────────────────────────────┐  │
                      │  │ ingress_gateway (:8000)          │  │
                      │  │ - Streamable HTTP (spec ≥2025)   │  │
                      │  │ - MCP Tools & REST JSON-RPC      │  │
                      │  └─────────────────┬────────────────┘  │
                      │                    │                   │
                      │  ┌─────────────────┴────────────────┐  │
                      │  │ ingress_gateway_assemblyai (:8002)  │  │
                      │  │ - WebSocket STT (/ws/speech)     │  │
                      │  └─────────────────┬────────────────┘  │
                      └────────────────────┼───────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           core_engine (:8001)                                   │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────┐  │
│  │ Policy Engine & Playbook│  │ CRIT Strategic Reasoning│  │ Dual-Payload    │  │
│  │ (Code-Enforced Tiers)   │  │ (AWS Bedrock Sonnet 3.5)│  │ Formatter Engine│  │
│  └────────────┬────────────┘  └────────────┬────────────┘  └────────┬────────┘  │
└───────────────┼────────────────────────────┼────────────────────────┼───────────┘
                │                            │                        │
                ▼                            │                        │
┌──────────────────────────────┐             │                        ▼
│ PostgreSQL Database (RDS)    │             │              ┌───────────────────┐
│ (AcroCorp Seed & Audit Logs) │             └─────────────>│ /events/ticker    │
└──────────────────────────────┘                            │ (SSE Push Channel)│
                                                            └─────────┬─────────┘
                                                                      │
                                                                      ▼
                                                            ┌───────────────────┐
                                                            │ Fire TV Adapter   │
                                                            │ (React 10-Foot UI)│
                                                            └───────────────────┘
```

---

## 3. AcroCorp Causal Storyline & Canonical Dataset

AcroCorp Global Technologies ($4.2B global tech & logistics enterprise) exhibits one interconnected operational crisis backing all voice queries, visual cards, and CRIT challenges.

### The Causal Chain
1. **Supplier X Raw Material Price Increase:** Cuts Region B margin by **-3.1 points** and creates a critical component shortage for Plant 3.
2. **Plant 3 Shutdown Risk ($1.2M Decision):** To prevent Plant 3 from shutting down within 48 hours, an emergency spot purchase of 50,000 components is requested ($1.2M, High Risk).
3. **Gate 4 Freight Logistics Rerouting:** Emergency freight rerouting surcharges cut Region B margin by an additional **-1.1 points** (Total Region B drop = **4.2 points**, bringing margin to **18.3%** vs 22.5% target, below the **20.0%** playbook floor).
4. **Month-End Close Blocked:** The same Gate 4 rerouting disruption delays physical inventory verification, blocking Step 3 of the Q3 Month-End Financial Close workflow.
5. **Ring Gate 4 Camera Snapshot:** Ring Gate 4 camera captures the priority freight delivery arriving at Gate 4—providing visual proof of the logistics rerouting and physical audit hold.

### Canonical Financial & Operational Figures
| Entity / Item | Value | Target / Baseline | Risk Tier | Source Table |
| :--- | :--- | :--- | :--- | :--- |
| **Q3 Revenue** | $1.24B | $1.30B (-4.6%) | — | `kpis` |
| **Region B Margin** | 18.3% | 22.5% (Floor: 20.0%) | — | `kpis`, `metric_drivers` |
| **Supplier X Driver** | -3.1 pts | -0.0 pts | — | `metric_drivers` |
| **Gate 4 Logistics Driver** | -1.1 pts | -0.0 pts | — | `metric_drivers` |
| **Emergency Spot Purchase** | $1,200,000 | Budget: $0 | **High** | `decision_items` |
| **MSA Liability Cap Override**| $450,000 | Threshold: $250k | **Medium** | `decision_items` |
| **Cloud Infrastructure SLA**| $12,000 | Within budget | **Low** | `decision_items` |
| **SaaS License Renewal** | $4,500 | Within budget | **Low** | `decision_items` |
| **RFQ Response Pipeline** | #12345 | 5 Steps | — | `workflow_instances` |
| **Month-End Close** | Blocked | Gate 4 Physical Audit | — | `workflow_instances` |

---

## 4. CRIT Strategic Reasoning & Code-Enforced Risk Tiers

CRIT operates in-process inside `core_engine`. Business policy logic is enforced **100% in code**, guaranteeing identical decision outcomes whether AWS Bedrock is online or falling back to deterministic templates.

### Policy Rules & Gate Tiers
```python
def evaluate_decision_risk_tier(decision: DecisionItem, playbook: StandingPlaybook) -> str:
    # High Risk Rule: Amount >= $1M OR decision breaches 20% regional margin floor
    if decision.amount >= Decimal("1000000.00") or playbook.breaches_margin_floor(decision):
        return "HIGH"
    
    # Medium Risk Rule: Amount between $50k and $1M OR liability cap > $250k threshold
    elif decision.amount >= Decimal("50000.00") or decision.category == "POLICY_OVERRIDE":
        return "MEDIUM"
    
    # Low Risk Rule: Delegated authority within pre-approved budget limits
    return "LOW"
```

| Risk Tier | Policy Criteria | Gate Experience | Voice Output | Fire TV Visual Output |
| :--- | :--- | :--- | :--- | :--- |
| **Low** | Amount < $50k, within delegated authority | **0 Turns** (Auto-Approved) | *"Approved Cloud SLA Amendment ($12k) and SaaS Renewal ($4.5k) under delegated authority."* | Status badge updates to `APPROVED`. |
| **Medium** | $50k–$1M or Liability Cap > $250k | **0 Turns** (On-Screen Warning) | *"MSA Liability Cap Override ($450k) exceeds $250k threshold. Please confirm execution."* | Displays `WARNING` badge & Legal Risk breakdown card. |
| **High** | Amount ≥ $1M or breaches 20% margin floor | **1 Turn** (CRIT Challenge) | Spoken persona question (*"CFO Persona"*): *"This $1.2M purchase recovers margin to 19.8% but uses 80% of Q3 contingency. Confirm?"* | Renders `audit` layout: Scorecard grid, Riskiest Assumption card, 7-Day Test checklist. |

---

## 5. Contract Specifications & Unified Schemas

All REST endpoints, MCP tool definitions, and Pydantic models share a single source of truth in `core_engine/schemas.py`.

### Unified Pydantic Schemas

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

class VisualCard(BaseModel):
    id: str
    title: str
    body: str
    meta: Optional[str] = ""
    severity: Literal["low", "info", "high", "critical"] = "info"
    value: Optional[str] = None
    target: Optional[str] = None
    trend: Optional[Literal["UP", "DOWN", "STABLE"]] = "STABLE"

class VisualPayload(BaseModel):
    layout: Literal["briefing", "decision", "status", "alerts", "audit"] = "briefing"
    title: str
    subtitle: Optional[str] = None
    ticker: Optional[str] = None
    cards: List[VisualCard] = []
    highlighted_card_id: Optional[str] = None
    extras: Optional[Dict[str, Any]] = {}

class VoicePayload(BaseModel):
    speech: str
    ssml: Optional[str] = None

class DualPayload(BaseModel):
    intent: str
    voice: VoicePayload
    visual: VisualPayload
    voice_summary: str = ""
    tool: Optional[str] = None
    tool_arguments: Optional[Dict[str, Any]] = {}
    session_id: Optional[str] = None
```

### Core MCP Tools Registry (`tools/list`)
Every MCP tool accepts `session_id` to maintain session context across multi-turn queries.

1. `get_executive_brief(session_id: str, org_id: str = "org_acme_corp")`
2. `explain_metric_change(session_id: str, metric_key: str, period: str = "Q3-2026", dimension: str = "Region B")`
3. `get_pending_decisions(session_id: str, risk_level: Optional[str] = None)`
4. `execute_decision(session_id: str, decision_id: str, choice: str = "approve", comment: Optional[str] = None)`
5. `start_workflow(session_id: str, workflow_type: str, context: Optional[Dict[str, Any]] = None)`
6. `get_recent_events(session_id: str, limit: int = 5)`

---

## 6. AWS Infrastructure & Demo Protection

The production architecture deploys to AWS ECS Fargate behind an Application Load Balancer (ALB) with PostgreSQL on RDS and static UI assets on S3 + CloudFront.

```
[Judges / Web Clients] ──> [CloudFront / S3 (Fire TV UI :5173)]
         │
         ├──> [ALB (HTTPS :443)]
                 │
                 ├──> [ECS Fargate: ingress_gateway (:8000)]
                 │         │ (Internal REST)
                 │         ▼
                 ├──> [ECS Fargate: core_engine (:8001)] ──> [AWS Bedrock Sonnet 3.5]
                 │         │                                [us-east-1]
                 │         ▼
                 └──> [RDS PostgreSQL (db.t4g.micro)]
```

### SSE Stream Resilience (`/events/ticker`)
* **ALB Idle Timeout:** Configured to `300 seconds`.
* **Heartbeat Stream:** `ingress_gateway` emits a comment ping (`: ping\n\n`) every 15 seconds.
* **Client Auto-Reconnect:** Fire TV React hook (`useVisualState`) automatically reconnects with exponential backoff if the socket drops.

### Demo Isolation & Judge Reset Endpoint
To prevent one judge's actions (e.g. approving the $1.2M decision) from corrupting the demo state for subsequent reviewers:
* **Reset Route:** `POST /admin/reset-scenario` (protected by `X-Admin-Token`).
* **Auto-Reset:** Automatically resets database seed state upon receiving a new `session_id` on `/mcp`.

---

## 7. Streamable HTTP MCP Compliance Checklist

For README documentation and video demonstration proof:
- [x] **Protocol Handshake:** `/mcp` negotiates `protocolVersion: "2025-11-25"`.
- [x] **Header Validation:** Validates `Mcp-Session-Id`, `Protocol-Version`, and `Origin`.
- [x] **Tool Discovery:** `tools/list` returns valid JSON-RPC schemas for all 6 tools.
- [x] **Third-Party Verification:** Verified using **Claude Desktop** and **MCP Inspector** (`npx @modelcontextprotocol/inspector`).
- [x] **Bearer Authentication:** Requires `Authorization: Bearer <token>` on public `/mcp` endpoints.

---

## 8. Final Implementation Roadmap to October 17

```
Oct 8-9: Linked Storyline Seed & Models
 └─► Lock executv-seed & Pydantic models (DualPayload, VisualPayload)
Oct 10-11: AWS ECS Infrastructure Slice
 └─► Deploy ECS Fargate, ALB (300s timeout), RDS Postgres & Bedrock Sonnet 3.5
Oct 12-13: Rule Tiering & CRIT Engine
 └─► Code-enforce Low/Med/High tiers & Bedrock Sonnet 3.5 1-turn challenge
Oct 14-15: Fire TV Audit UI & Reset Endpoint
 └─► Render audit layout, persona badges & POST /admin/reset-scenario
Oct 16-17: Code Freeze & Dry-Run Testing
 └─► 2 consecutive flawless runs on AWS; freeze codebase for video recording
```
