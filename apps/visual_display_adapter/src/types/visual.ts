/** Types aligned with core_engine OpenAPI DualPayload + ingress ticker events. */

export type Severity = "low" | "info" | "high" | "critical";
export type TickerStatus = "EXECUTING" | "COMPLETED" | "FAILED";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | string;

export type ViewId =
  | "EXECUTIVE_BRIEF"
  | "ANALYSIS_DEEP_DIVE"
  | "DECISIONS_LIST"
  | "WORKFLOW_TRACKER"
  | "AUDIT_SCORECARD"
  | string;

export type VoicePayload = {
  narration_text: string;
  suggested_followups: string[];
};

export type VoiceSummary = VoicePayload;

export type RiskAnalysis = {
  financial_risk?: string;
  legal_compliance?: string;
  legal_flag?: string;
  budget_status?: string;
  margin_impact?: string;
  urgency?: string;
  [key: string]: string | undefined;
};

export type VisualCard = {
  id: string;
  type?: string;
  title: string;
  body: string;
  meta: string;
  severity: Severity;
  value?: string;
  target?: string;
  trend?: string;
};

export type BoardCard = VisualCard;

export type VisualComponent = {
  id: string;
  type: string;
  title?: string;
  value?: string;
  target?: string;
  trend?: string;
  items?: Array<Record<string, unknown>>;
};

export type VisualPayload = {
  view_id: ViewId;
  header_title: string;
  badge_status: string;
  layout?: string;
  highlight_target_id?: string;
  highlighted_card_id?: string;
  components: VisualComponent[];
  updated_item?: {
    id: string;
    title: string;
    status: string;
  };
};

export type VisualStateModel = VisualPayload;

export type DualPayload = {
  voice_summary: VoicePayload;
  visual_state_model: VisualPayload;
};

export type TickerEvent = {
  timestamp: string;
  tool_name: string;
  status: TickerStatus | string;
  args: Record<string, unknown>;
  latency_ms: number;
  detail?: string;
};

export type KpiItem = {
  id: string;
  metric: string;
  dimension: string;
  value: string;
  target: string;
  trend: string;
};

export type AlertItem = {
  id: string;
  location: string;
  description: string;
  priority: string;
  source: string;
  event_type: string;
  image_url?: string | null;
  occurred_at?: string | null;
};

export type DriverItem = {
  id: string;
  driver: string;
  impact: string;
  summary: string;
};

export type DecisionVisualItem = {
  id: string;
  title: string;
  category: string;
  amount: string;
  risk_level: RiskLevel;
  status: string;
  recommendation: string;
  context_summary?: string;
  policy_flag?: string;
  risk_analysis?: RiskAnalysis;
};

export type WorkflowStepItem = {
  id: string;
  step_number: number;
  title: string;
  owner: string;
  status: string;
  blocker_reason?: string | null;
};

export const CORE_ENGINE_URL =
  import.meta.env.VITE_CORE_ENGINE_URL ?? "http://localhost:8001";
export const INGRESS_GATEWAY_URL =
  import.meta.env.VITE_INGRESS_GATEWAY_URL ?? "http://localhost:8000";

export const CAMERA_SNAPSHOT =
  "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=800&auto=format&fit=crop";

export const FALLBACK_PAYLOAD: DualPayload = {
  voice_summary: {
    narration_text: "Loading the AcroCorp briefing from the seed.",
    suggested_followups: [
      "Give me today's brief.",
      "Why is margin down in Region B?",
      "What decisions need me?",
    ],
  },
  visual_state_model: {
    view_id: "EXECUTIVE_BRIEF",
    header_title: "AcroCorp Global Command View",
    badge_status: "LOADING",
    components: [],
  },
};

function asText(value: unknown, fallback = ""): string {
  return value == null ? fallback : String(value);
}

export function parseMetricNumber(value: string | undefined): number {
  if (!value) {
    return 0;
  }
  const match = value.match(/-?\d[\d,]*(?:\.\d+)?/);
  if (!match) {
    return 0;
  }
  const numeric = Number(match[0].replace(/,/g, ""));
  if (!Number.isFinite(numeric)) {
    return 0;
  }
  const tail = value.slice((match.index ?? 0) + match[0].length).trim().toLowerCase();
  if (tail.startsWith("b")) {
    return numeric * 1000;
  }
  if (tail.startsWith("k")) {
    return numeric / 1000;
  }
  return numeric;
}

export function severityFor(value: string | undefined): Severity {
  const token = (value ?? "").toUpperCase();
  if (
    ["DOWN", "HIGH", "CRITICAL_ATTENTION", "ATTENTION_REQUIRED", "FAILED", "BLOCKED", "CRITICAL"].includes(
      token,
    )
  ) {
    return "high";
  }
  if (["PENDING_ACTION", "IN_PROGRESS", "MEDIUM", "EXECUTING", "REVIEW"].includes(token)) {
    return "info";
  }
  return "low";
}

function fromItems<T>(
  items: Array<Record<string, unknown>> | undefined,
  map: (item: Record<string, unknown>) => T,
): T[] {
  return (items ?? []).map(map);
}

export function componentByType(visual: VisualPayload, type: string): VisualComponent | undefined {
  return visual.components.find((component) => component.type === type);
}

export function kpiItems(visual: VisualPayload): KpiItem[] {
  const grid = componentByType(visual, "KPI_GRID");
  if (grid) {
    return fromItems(grid.items, (item) => ({
      id: asText(item.id),
      metric: asText(item.metric, "KPI"),
      dimension: asText(item.dimension),
      value: asText(item.value),
      target: asText(item.target),
      trend: asText(item.trend, "STABLE"),
    }));
  }
  const metric = componentByType(visual, "METRIC_CARD");
  if (!metric) {
    return [];
  }
  return [
    {
      id: metric.id,
      metric: asText(metric.title, "Metric"),
      dimension: visual.header_title,
      value: asText(metric.value),
      target: asText(metric.target),
      trend: asText(metric.trend, "STABLE"),
    },
  ];
}

export function alertItems(visual: VisualPayload): AlertItem[] {
  return fromItems(componentByType(visual, "ALERTS_TIMELINE")?.items, (item) => ({
    id: asText(item.id),
    location: asText(item.location, "Site"),
    description: asText(item.description, "Alert"),
    priority: asText(item.priority, "MEDIUM"),
    source: asText(item.source),
    event_type: asText(item.event_type),
    image_url: item.image_url ? asText(item.image_url) : null,
    occurred_at: item.occurred_at ? asText(item.occurred_at) : null,
  }));
}

export function driverItems(visual: VisualPayload): DriverItem[] {
  return fromItems(componentByType(visual, "DRIVER_BREAKDOWN_LIST")?.items, (item) => ({
    id: asText(item.id),
    driver: asText(item.driver, "Driver"),
    impact: asText(item.impact),
    summary: asText(item.summary),
  }));
}

function asRiskAnalysis(value: unknown): RiskAnalysis | undefined {
  if (!value || typeof value !== "object") {
    return undefined;
  }
  const record = value as Record<string, unknown>;
  const analysis: RiskAnalysis = {};
  for (const [key, entry] of Object.entries(record)) {
    if (entry != null) {
      analysis[key] = String(entry);
    }
  }
  return analysis;
}

export function decisionItems(visual: VisualPayload): DecisionVisualItem[] {
  return fromItems(componentByType(visual, "DECISION_CARD_LIST")?.items, (item) => ({
    id: asText(item.id),
    title: asText(item.title, "Decision"),
    category: asText(item.category),
    amount: asText(item.amount),
    risk_level: asText(item.risk_level, "LOW"),
    status: asText(item.status, "PENDING"),
    recommendation: asText(item.recommendation || item.recommended_choice, "REVIEW"),
    context_summary: item.context_summary ? asText(item.context_summary) : undefined,
    policy_flag: item.policy_flag ? asText(item.policy_flag) : undefined,
    risk_analysis: asRiskAnalysis(item.risk_analysis),
  }));
}

export type PersonaBadge = { id: string; persona: string; verdict: string };
export type ProtocolStep = { id: string; title: string };

export function personaBadges(visual: VisualPayload): PersonaBadge[] {
  return fromItems(componentByType(visual, "PERSONA_BADGE_GRID")?.items, (item) => ({
    id: asText(item.id),
    persona: asText(item.persona, "Persona"),
    verdict: asText(item.verdict),
  }));
}

export function protocolSteps(visual: VisualPayload): ProtocolStep[] {
  return fromItems(componentByType(visual, "PROTOCOL_CHECKLIST")?.items, (item) => ({
    id: asText(item.id),
    title: asText(item.title),
  }));
}

export function assumptionText(visual: VisualPayload): string {
  const card = componentByType(visual, "RISKIEST_ASSUMPTION");
  const first = card?.items?.[0];
  if (first && typeof first.body === "string") {
    return first.body;
  }
  return "";
}

export function workflowStepItems(visual: VisualPayload): WorkflowStepItem[] {
  return fromItems(componentByType(visual, "WORKFLOW_STEP_LIST")?.items, (item) => ({
    id: asText(item.id),
    step_number: Number(item.step_number ?? 0),
    title: asText(item.title, "Step"),
    owner: asText(item.owner),
    status: asText(item.status, "NOT_STARTED"),
    blocker_reason: item.blocker_reason ? asText(item.blocker_reason) : null,
  }));
}

export function cardsFromVisual(visual: VisualPayload): VisualCard[] {
  return visual.components.flatMap((component) => {
    if (component.type === "KPI_GRID") {
      return kpiItems({ ...visual, components: [component] }).map((item) => ({
        id: item.id,
        type: component.type,
        title: item.metric,
        body: `${item.dimension} · trend ${item.trend}`,
        meta: item.dimension || item.trend,
        severity: severityFor(item.trend),
        value: item.value,
        target: item.target,
        trend: item.trend,
      }));
    }
    if (component.type === "ALERTS_TIMELINE") {
      return alertItems({ ...visual, components: [component] }).map((item) => ({
        id: item.id,
        type: component.type,
        title: item.description,
        body: item.location,
        meta: item.priority,
        severity: severityFor(item.priority),
      }));
    }
    if (component.type === "METRIC_CARD") {
      return [
        {
          id: component.id,
          type: component.type,
          title: asText(component.title, "Metric"),
          body: `Trend ${asText(component.trend, "STABLE")}`,
          meta: asText(component.trend, "METRIC"),
          severity: severityFor(component.trend),
          value: asText(component.value),
          target: asText(component.target),
          trend: component.trend,
        },
      ];
    }
    if (component.type === "DRIVER_BREAKDOWN_LIST") {
      return driverItems({ ...visual, components: [component] }).map((item) => ({
        id: item.id,
        type: component.type,
        title: item.driver,
        body: item.summary,
        meta: item.impact,
        severity: "high" as const,
        value: item.impact,
      }));
    }
    if (component.type === "DECISION_CARD_LIST") {
      return decisionItems({ ...visual, components: [component] }).map((item) => ({
        id: item.id,
        type: component.type,
        title: item.title,
        body: `${item.category} · ${item.amount} · recommend ${item.recommendation}`,
        meta: item.risk_level,
        severity: severityFor(item.risk_level),
        value: item.amount,
      }));
    }
    if (component.type === "WORKFLOW_STEP_LIST") {
      return workflowStepItems({ ...visual, components: [component] }).map((item) => ({
        id: item.id,
        type: component.type,
        title: `Step ${item.step_number} · ${item.title}`,
        body: `Owner ${item.owner}`,
        meta: item.status,
        severity: severityFor(item.status),
      }));
    }
    if (component.type === "RISKIEST_ASSUMPTION" || component.type === "CHALLENGE_PROMPT") {
      const first = component.items?.[0];
      return [
        {
          id: component.id,
          type: component.type,
          title: asText(component.title, "Audit"),
          body: asText(first && typeof first === "object" ? first.body : ""),
          meta: component.type,
          severity: "critical",
        },
      ];
    }
    if (component.type === "PERSONA_BADGE_GRID" || component.type === "PROTOCOL_CHECKLIST") {
      return fromItems(component.items, (item) => ({
        id: asText(item.id),
        type: component.type,
        title: asText(item.persona || item.title, "Item"),
        body: asText(item.verdict || item.title),
        meta: component.type,
        severity: "info" as const,
      }));
    }
    if (component.type === "CARD_LIST") {
      return fromItems(component.items, (item) => ({
        id: asText(item.id),
        type: component.type,
        title: asText(item.title, "Card"),
        body: asText(item.body),
        meta: asText(item.meta || item.severity, "INFO"),
        severity: severityFor(asText(item.severity)),
        value: item.value == null ? undefined : asText(item.value),
        target: item.target == null ? undefined : asText(item.target),
      }));
    }
    return [];
  });
}

export function resolveHighlight(visual: VisualPayload, cards: VisualCard[]): string | null {
  const target = visual.highlighted_card_id || visual.highlight_target_id;
  if (!target) {
    return null;
  }
  if (cards.some((card) => card.id === target)) {
    return target;
  }
  const component = visual.components.find((item) => item.id === target);
  const first = component?.items?.[0];
  if (first && typeof first === "object" && first.id != null) {
    return String(first.id);
  }
  return null;
}

function layoutToView(layout: unknown): ViewId {
  switch (String(layout)) {
    case "decision":
      return "DECISIONS_LIST";
    case "status":
      return "WORKFLOW_TRACKER";
    case "alerts":
      return "EXECUTIVE_BRIEF";
    case "audit":
      return "AUDIT_SCORECARD";
    default:
      return "EXECUTIVE_BRIEF";
  }
}

export function asDualPayload(value: unknown): DualPayload | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const root = value as Record<string, unknown>;
  const payload = (root.payloads && typeof root.payloads === "object" ? root.payloads : root) as Record<
    string,
    unknown
  >;
  const modern = payload.visual_state_model;
  if (modern && typeof modern === "object") {
    const voice = payload.voice_summary;
    const voiceRecord = voice && typeof voice === "object" ? (voice as Record<string, unknown>) : {};
    const visualRecord = modern as Record<string, unknown>;
    if (!Array.isArray(visualRecord.components)) {
      return null;
    }
    return {
      voice_summary: {
        narration_text: asText(
          voiceRecord.narration_text || (typeof payload.voice_summary === "string" ? payload.voice_summary : ""),
        ),
        suggested_followups: Array.isArray(voiceRecord.suggested_followups)
          ? voiceRecord.suggested_followups.map((item) => String(item))
          : [],
      },
      visual_state_model: {
        view_id:
          visualRecord.layout === "audit"
            ? "AUDIT_SCORECARD"
            : asText(visualRecord.view_id, "EXECUTIVE_BRIEF"),
        header_title: asText(visualRecord.header_title, "ExecuTV"),
        badge_status: asText(visualRecord.badge_status, "HEALTHY"),
        layout: visualRecord.layout ? asText(visualRecord.layout) : undefined,
        highlight_target_id: visualRecord.highlight_target_id
          ? asText(visualRecord.highlight_target_id)
          : undefined,
        highlighted_card_id: visualRecord.highlighted_card_id
          ? asText(visualRecord.highlighted_card_id)
          : undefined,
        components: visualRecord.components as VisualComponent[],
      },
    };
  }

  const legacyVisual = payload.visual;
  if (!legacyVisual || typeof legacyVisual !== "object") {
    return null;
  }
  const visual = legacyVisual as Record<string, unknown>;
  const voice = payload.voice && typeof payload.voice === "object" ? (payload.voice as Record<string, unknown>) : {};
  const cards = Array.isArray(visual.cards) ? visual.cards : [];
  return {
    voice_summary: {
      narration_text: asText(payload.voice_summary || voice.speech),
      suggested_followups: [],
    },
    visual_state_model: {
      view_id: layoutToView(visual.layout),
      header_title: asText(visual.title, "ExecuTV"),
      badge_status: asText(visual.subtitle, "HEALTHY"),
      layout: visual.layout ? asText(visual.layout) : undefined,
      highlight_target_id: visual.highlighted_card_id
        ? asText(visual.highlighted_card_id)
        : visual.highlight_target_id
          ? asText(visual.highlight_target_id)
          : undefined,
      highlighted_card_id: visual.highlighted_card_id ? asText(visual.highlighted_card_id) : undefined,
      components: [
        {
          id: "cards",
          type: "CARD_LIST",
          items: cards as Array<Record<string, unknown>>,
        },
      ],
    },
  };
}

export function asTickerEvent(value: unknown): TickerEvent | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const row = value as Record<string, unknown>;
  if (typeof row.tool_name !== "string" || !row.tool_name) {
    return null;
  }
  const args = row.args && typeof row.args === "object" ? (row.args as Record<string, unknown>) : {};
  return {
    timestamp: asText(row.timestamp ?? row.ts),
    tool_name: row.tool_name,
    status: asText(row.status),
    args,
    latency_ms: typeof row.latency_ms === "number" ? row.latency_ms : 0,
    detail: row.detail ? asText(row.detail) : undefined,
  };
}

export function screenLabel(viewId: ViewId): string {
  switch (viewId) {
    case "ANALYSIS_DEEP_DIVE":
      return "Analysis Deep Dive";
    case "DECISIONS_LIST":
      return "Decisions & Approvals";
    case "WORKFLOW_TRACKER":
      return "Workflow Tracker";
    case "AUDIT_SCORECARD":
      return "Audit Scorecard";
    default:
      return "Executive Brief";
  }
}

export type ScreenTool = {
  id: ViewId;
  label: string;
  tool: string;
  args: Record<string, unknown>;
};

export const SCREEN_TOOLS: ScreenTool[] = [
  { id: "EXECUTIVE_BRIEF", label: "Executive Brief", tool: "get_executive_brief", args: {} },
  {
    id: "ANALYSIS_DEEP_DIVE",
    label: "Analysis Deep Dive",
    tool: "explain_metric_change",
    args: { metric_name: "margin", dimension: "Region B", window: "Q3-2026" },
  },
  { id: "DECISIONS_LIST", label: "Decisions & Approvals", tool: "get_pending_decisions", args: {} },
  {
    id: "WORKFLOW_TRACKER",
    label: "Month-end close",
    tool: "get_workflow_status",
    args: { workflow_name: "month-end close" },
  },
];

