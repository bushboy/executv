# ExecuTV Architecture Spec v2

Oct 7, 2026 · @Bushboy

## Summary

ExecuTV's five services already run end to end; v2 spends the remaining days before the October 17 code freeze on three things: a linked AcroCorp storyline, deterministic CRIT risk tiers, and an AWS deployment with Bedrock as the primary model. This spec replaces v1 and describes the system as built, not as first imagined.

The Amazon submission uses the self-hosted Streamable HTTP MCP server with a simulated Alexa+ web client, which the Devpost rules allow. The submission says so plainly, and third-party MCP clients (MCP Inspector, Claude) prove the server is spec-compliant.

| Area | v1 | v2 |
| --- | --- | --- |
| CRIT runtime | `sidecar.py` spawned per request, hardware probe, 15 s timeout | Runs in-process in `core_engine`; no sidecar tier |
| LLM | `gemini` or `seeded` | Bedrock Converse primary (`bedrock`), `seeded` fallback |
| Alexa+ | Implied real Alexa+ | Simulated web client, disclosed; MCP validated with third-party clients |
| Voice-visual sync | Client parses SSML tags | The tool handler sets the highlight and pushes `visual_state_model` over SSE |
| Challenge gate | Up to 3 turns | 0 or 1 turn, chosen by code from playbook rules |
| Company data | Canned KPIs, figures disagree across spec and script | One linked AcroCorp seed is the source of every number |
| Hosting | Local, ngrok for judges | AWS: containers + RDS + static TV UI |
| Roadmap | Starts from a skeleton | Starts from the working build |

## System topology

All requests enter through `ingress_gateway`; `core_engine` holds the orchestration, the policy engine and CRIT, and pushes each screen to the TV over SSE.

&#91;embedded content: ExecuTV topology · 8 components\]

**Request flow for one decision**

1. A client calls an MCP tool on `/mcp`, e.g. `execute_decision`.
2. `ingress_gateway` forwards it to `core_engine`, which reads the seed from PostgreSQL and applies the playbook rules.
3. `core_engine` returns `voice_summary` to the client and publishes `visual_state_model` with `highlighted_card_id` to `/events/ticker`.
4. The TV, subscribed to the SSE stream, switches layout and highlights the card.

**Pairing.** The demo uses one global SSE channel, so every call drives the single TV. For multiple executives, the TV would show a pairing code at launch and each MCP session would publish only to its paired channel. This is documented as future work, not built for the hackathon.

## AcroCorp storyline

AcroCorp Global Technologies ($4.2B, global tech and logistics) has one connected problem: a supplier price shock and a logistics bottleneck are pulling Region B below the 20% margin floor, and the executive must decide whether to spend $1.2M to keep a plant running. Every number the system speaks or shows comes from the `executv-seed` scenario; nothing is typed into prompts, scripts or spec examples by hand.

**The causal chain the seed must encode**

1. Supplier X raises raw material prices. This cuts Region B margin by 3.1 points and creates a component shortage.
2. The shortage puts a plant at risk of shutdown, which creates the $1.2M emergency spot-procurement request (high risk).
3. Logistics rerouting at Gate 4 adds surcharges, cutting Region B margin by a further 1.1 points.
4. The same Gate 4 disruption blocks the physical audit, so the Q3 month-end close is stuck.
5. A Ring camera records the rerouted freight arriving, the physical evidence behind steps 3 and 4.

Result: Region B margin is 18.3% against a 22.5% target (3.1 + 1.1 = 4.2 points), and below the 20% playbook floor.

**Canonical figures**

| Item | Value | Risk tier | Source table |
| --- | --- | --- | --- |
| Q3 revenue | $1.24B vs $1.30B target (4.6% under) | — | `kpis` |
| Region B margin | 18.3% vs 22.5% target; floor 20% | — | `kpis`, `metric_drivers` |
| Supplier X driver | −3.1 pts | — | `metric_drivers` |
| Gate 4 rerouting driver | −1.1 pts | — | `metric_drivers` |
| Emergency spot procurement | $1.2M | High | `decision_items` |
| MSA liability cap override | $450k | Medium | `decision_items` |
| Cloud SLA amendment | $12k | Low | `decision_items` |
| License renewal | $4.5k | Low | `decision_items` |
| RFQ response | #12345 | — | `workflow_instances` |
| Q3 month-end close | Blocked at Gate 4 physical audit | — | `workflow_instances`, `workflow_steps` |

**Fixes to make in the seed**

- Retire "revenue up 8%", "$4.2M MTD" and "discounts over 12%" everywhere. The briefing opener becomes: Q3 revenue is $1.24B versus $1.30B, 4.6% under target, and Region B margin is 18.3%, below the 20.0% floor.
- Rename for clarity. "Region B", "Gate 4" and the Ring camera at "Gate B" read as three different places, and judges will confuse them. Put the Ring camera at Gate 4.
- Present the two small decisions as auto-approved under delegated authority, summarized in one line. A CEO of a $4.2B company would not review a $4.5k renewal one by one.
- Add the two numbers CRIT needs to reason about the $1.2M decision: the margin effect of approving it, and the cost of a plant shutdown if declined. Without them the challenge has nothing to weigh.

**Golden questions** (each answer is generated from the seed and checked as an automated test)

- "Give me today's brief."
- "Why is margin down in Region B?"
- "What decisions need me?"
- "Approve the spot purchase." (triggers the one-turn challenge)
- "Why is the month-end close blocked?"

## CRIT integration

Code decides; Bedrock explains and challenges. The playbook rules set the risk tier and whether a decision can execute, so the Bedrock path and the offline path always reach the same verdict.

**Where CRIT applies**

| MCP mode | CRIT role | Model use |
| --- | --- | --- |
| Briefing | None; deterministic summary of the seed | Optional phrasing only |
| Analysis ("why?") | Strategy mode: explains drivers with the standing playbook injected | Bedrock narrates the computed drivers |
| Decision | Strategy mode: risk-weighted challenge gate and audit card | Bedrock writes the challenge and the card |
| Process | Execution mode: process packs (RFQ, month-end close) | Step summaries only |

**Risk tiers, evaluated in code** (proposed thresholds; set the final values in the playbook)

| Tier | Rule | Gate | What the executive hears |
| --- | --- | --- | --- |
| Low | Within delegated authority, no playbook rule crossed | 0 turns, auto-approved | One-line summary of what was approved |
| Medium | One threshold crossed, e.g. liability above $250k | 0 turns, explicit confirmation | "This exceeds the $250k liability threshold. Confirm?" |
| High | Amount at or above $1M, or the decision moves a region below the 20% margin floor | 1 challenge turn, then confirmation | One sharp persona question, then the riskiest assumption |

**High-risk flow**

1. `execute_decision` arrives. The policy engine evaluates the rules and returns High.
2. The handler returns at once with a templated challenge question built from the rule that fired. Alexa speaks it with no model wait.
3. In parallel, Bedrock writes the audit card. The handler pushes it to the TV over SSE when ready; the seeded card is pushed if Bedrock fails or times out.
4. The executive answers. A second `execute_decision` call carries the answer, the gate opens, and the decision asks for final confirmation.

**Gate state** is keyed by `decision_id` plus a session id, stored in `decision_audit_logs` or a CRIT session table. Every tool that touches a decision takes `session_id`; otherwise the gate resets between calls.

**Personas.** One persona speaks the challenge, chosen by decision domain: CFO for procurement and pricing, Legal/Compliance for contract overrides. The TV shows all three persona badges (CFO, Legal/Compliance, Ops Lead) with a one-line verdict each.

**Audit card on the TV** (new `audit` layout): a scorecard grid, the riskiest assumption as its own card, and the 7-day test protocol as a short checklist. Alexa speaks only the challenge question and the riskiest assumption.

**Playbook injection.** The 20% margin floor and the $250k liability threshold are injected into every prompt so Bedrock's language matches the rules. Injection informs the wording; it never decides.

## Contracts and MCP compliance

The code's Pydantic models are the contract; the REST OpenAPI schema, the MCP tool schemas and this spec are all generated from or checked against them. v1's hand-written schemas had already drifted.

**DualPayload as built:** `voice_summary` plus `visual_state_model`. Use these names in the spec, the README and the video; drop v1's `voice` / `visual` naming.

**Contract fixes**

| Issue in v1 | Fix |
| --- | --- |
| MCP uses `metric` / `period`, REST uses `metric_name` / `window` | One parameter name per concept, shared by both |
| `workflow_name` defaults to `"12345"` | No demo IDs as defaults; the seed supplies them |
| Severity is `low` / `info` / `high`, but the ticker says "CRITICAL" | Add `critical` to the enum, or stop using the word |
| Layouts lack a view for CRIT output | Add `audit` to the layout enum |
| Decision tools carry no session | Add `session_id` to every decision and CRIT tool |
| Highlighting relies on SSML tags | The handler sets `highlighted_card_id`; SSML is optional decoration |

**What proves MCP compliance** (put these in the README and the video)

- [ ] `initialize` on `/mcp` negotiates protocol version `2025-11-25`.
- [ ] Session id and protocol-version headers handled as the spec requires; `Origin` validated.
- [ ] `tools/list` returns every tool with a complete input schema.
- [ ] MCP Inspector session screenshot, against the AWS endpoint.
- [ ] Claude connected to the AWS endpoint as a remote MCP server, calling `get_executive_brief`.
- [ ] Bearer token required on `/mcp`.

The extra `/mcp/v1/tools/call` route can stay as a test helper, but it is not part of Streamable HTTP. Leave it out of compliance claims.

## AWS deployment and demo protection

Run the containers on ECS Fargate behind an Application Load Balancer, with RDS PostgreSQL and the TV UI on S3 + CloudFront. ECS is preferred over App Runner because the long-lived SSE stream needs a tunable idle timeout; check App Runner's current request timeout before choosing it.

| Component | AWS service | Notes |
| --- | --- | --- |
| `ingress_gateway` (MCP + SSE) | ECS Fargate behind ALB | Public HTTPS; ALB idle timeout raised above the heartbeat interval |
| `core_engine` | ECS Fargate, internal | Reached only from the gateway |
| `ingress_gateway_assemblyai` | ECS Fargate behind ALB | Needed for the LabLab.ai path |
| PostgreSQL | RDS, smallest instance | Seeded by `executv-seed` on deploy |
| Fire TV UI | S3 + CloudFront | Vite build pointed at the AWS endpoints |
| Secrets (AssemblyAI key, bearer token) | Secrets Manager | Never in the client bundle |
| Reasoning model | Bedrock Converse API | Enable model access in the region on day 2 |

**SSE resilience.** Send a heartbeat comment every 15 to 20 seconds, and make the TV client reconnect automatically and re-fetch current state on reconnect.

**Protecting the demo from judges**

- A bearer token on `/mcp`, given in the submission notes.
- `POST /admin/reset-scenario` (token-protected) restores the seed, so one judge approving the $1.2M purchase does not change the demo for the next. Optionally reset on each new MCP session.
- Basic rate limiting on the public endpoints.
- Share the endpoint URL and token, never AWS account access. Repo access goes to `testing@devpost.com` and the named Amazon reviewers.
- Keep the stack running through judging, then tear it down to stop costs.

## Plan to October 17

The storyline comes first because every later item depends on its numbers, and AWS goes second so deployment problems surface early. The Devpost deadline is Oct 23 at 12:00 PDT, which is 21:00 in Johannesburg.

&#91;embedded content: schedule · Oct 8 to Oct 23\]

| Workstream | Done when |
| --- | --- |
| Linked storyline seed | All five golden questions pass as tests; no retired figure appears in code, spec or script |
| AWS slice + Bedrock | Current build runs on AWS; Inspector connects with the token; Bedrock model access enabled |
| Risk tiers + gate | All four decisions reach the right tier with Bedrock switched off |
| Bedrock wiring | Explanations and audit cards come from Bedrock; killing Bedrock falls back to seeded output with no errors |
| Audit UI, reset, auth | `audit` layout and persona badges render on the TV; reset endpoint restores the seed |
| Code freeze, dry run | The full 3-minute demo runs on AWS twice in a row without a fix in between |
| Video, friction log | Video recorded from the AWS deployment; friction log entries written up from notes kept since Oct 9 |

Keep friction-log notes from the first AWS deploy onward; reconstructing them on Oct 19 loses the detail judges reward.

## Risks and open items

The largest remaining risk is schedule, not architecture: a solo builder has ten days to freeze and six more for the video and submission.

| Risk | Impact | Mitigation | Fallback |
| --- | --- | --- | --- |
| AWS deployment surprises late in the schedule | High | Deploy a thin slice on Oct 9–10, redeploy as features land | Local Docker stack + stable tunnel for the video only |
| SSE stream cut by proxy timeouts | High | Heartbeats, raised ALB idle timeout, client auto-reconnect | TV polls current state every few seconds |
| Bedrock slow or unavailable | Medium | Templated challenge spoken first; card streamed later | Seeded audit card and seeded explanations |
| Judges change shared demo state | Medium | Reset endpoint, per-session reset | Reset before each review window |
| Story figures drift again | Medium | Golden-question tests generated from the seed | — |
| Simulated Alexa+ read as a mock | Medium | Disclosure, Inspector and Claude as third-party clients | — |
| Two competitions split focus | Medium | Amazon path first until Oct 17 | LabLab.ai video reuses the Amazon build |

**Open items**

- [ ] Seed values for the margin effect of approving the $1.2M purchase, and the cost of a shutdown if declined.
- [ ] Final risk-tier thresholds in the playbook.
- [ ] Which Bedrock model, and in which region.
- [ ] LabLab.ai deadline, and whether its rules allow the same project in another competition.
- [ ] Whether Bee events stay in scope (the Acme volume signal is not in the current seed).
