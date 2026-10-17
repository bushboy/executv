# Product feedback

Use this while testing ExecuTV against Alexa+, Fire TV, MCP, and Ring-style operational ingest. One observation per block. Copy the template as needed.

## Feedback template

**ID:** PF-0X
**Date:** YYYY-MM-DD
**Surface:** Alexa+ / Fire TV / MCP / Ring ingest / Gemini / other
**Persona:** Executive in a boardroom with a Fire TV + Echo
**What I wanted:**
**What I got:**
**Why it matters:**
**Suggested change:**
**Severity:** blocker / confusing / polish
**NPS-style (0–10):**

---

**ID:** PF-01
**Date:**
**Surface:** Alexa+ MCP tool list
**Persona:**
**What I wanted:** The six executive tools (`get_executive_brief`, `explain_metric_change`, `get_pending_decisions`, `execute_decision`, `start_workflow`, `get_recent_events`) to be obvious to Alexa+.
**What I got:**
**Why it matters:**
**Suggested change:**
**Severity:**
**NPS-style (0–10):**

---

**ID:** PF-02
**Date:**
**Surface:** Fire TV 10-foot Live Alerts
**Persona:**
**What I wanted:** Ring / delivery / site alerts glanceable from the couch without leaving the brief.
**What I got:**
**Why it matters:**
**Suggested change:**
**Severity:**
**NPS-style (0–10):**

---

**ID:** PF-03
**Date:**
**Surface:** Dual payload (voice_summary + visual)
**Persona:**
**What I wanted:** Alexa to speak a short `voice_summary` while Fire TV shows the cards.
**What I got:**
**Why it matters:**
**Suggested change:**
**Severity:**
**NPS-style (0–10):**

---

**ID:** PF-04
**Date:**
**Surface:** Gemini reasoning (`POST /api/v1/reason`)
**Persona:**
**What I wanted:** Natural language → MCP tool + arguments, even without a key (seeded fallback).
**What I got:**
**Why it matters:**
**Suggested change:**
**Severity:**
**NPS-style (0–10):**

---

## Summary for judges

See the completed track table in [docs/friction-log.md](friction-log.md#product-feedback-summary).

| Product / Tool | Onboarding Experience | What Worked Well | What Needs Improvement | Would Build With Again? |
| :--- | :--- | :--- | :--- | :--- |
| **Alexa+ (MCP Spec)** | Excellent open standard framework. | Decoupled JSON-RPC tool schemas made agentic integration straightforward. | Clearer documentation on Streamable HTTP session header requirements. | **Yes** |
| **Fire TV / Vega Simulator** | Fast local setup via browser viewports. | Rendering standard React web apps on a 10-foot visual screen is low-friction. | Need out-of-the-box spatial focus libraries for React/JS apps. | **Yes** |
| **Ring Event Ingestion** | Fully accessible via REST webhooks. | Simple data contract to normalize site/security alerts into business logic. | A built-in event mock sandbox in the developer portal would speed up dev time. | **Yes** |

- Top 3 product wins:
  1. Streamable HTTP MCP as the Alexa+ tool bus
  2. Dual payload (voice_summary + 10-foot visual)
  3. Hardware-free Ring ingest onto Live Alerts
- Top 3 product gaps:
  1. No official `alexa-mcp-validator` for Streamable HTTP
  2. No React spatial-focus template in Vega docs
  3. No Ring event sandbox in the developer portal
- Would we ship this to a real executive boardroom? not yet — demo-complete; needs production auth and hardware soak.
