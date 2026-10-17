import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AudioLines,
  Building,
  MicVocal,
  Radio,
  ShieldAlert,
  Sparkles,
  Thermometer,
  TrendingDown,
  TrendingUp,
  Workflow,
} from "lucide-react";

import { MetricChartCard } from "./components/Charts/MetricChartCard";
import { FocusWrapper, TvFocusRoot } from "./components/FocusWrapper";
import { RingCameraCard } from "./components/RingCameraCard";
import { RiskMeter } from "./components/RiskMeter";
import { TickerSidebar } from "./components/TickerSidebar";
import { VoiceWaveform } from "./components/VoiceWaveform";
import { useVisualState } from "./hooks/useVisualState";
import {
  FALLBACK_PAYLOAD,
  SCREEN_TOOLS,
  alertItems,
  assumptionText,
  cardsFromVisual,
  decisionItems,
  driverItems,
  kpiItems,
  personaBadges,
  protocolSteps,
  resolveHighlight,
  screenLabel,
  workflowStepItems,
  type AlertItem,
  type DecisionVisualItem,
  type DriverItem,
  type KpiItem,
  type ViewId,
  type VisualPayload,
  type WorkflowStepItem,
} from "./types/visual";

const JUDGE_PROMPTS = [
  "Give me today's brief.",
  "Why is margin down in Region B?",
  "What decisions need me?",
  "Approve the spot purchase.",
  "Why is the month-end close blocked?",
];

function MiniKpi({ item, highlightId }: { item: KpiItem; highlightId: string | null }) {
  const down = item.trend === "DOWN";
  return (
    <FocusWrapper id={item.id} isHighlighted={item.id === highlightId} className="py-4">
      <div className="flex items-start justify-between">
        <p className="text-xs font-bold tracking-[0.18em] text-slate-400 uppercase">{item.metric}</p>
        {down ? (
          <TrendingDown className="h-5 w-5 text-rose-400" />
        ) : (
          <TrendingUp className="h-5 w-5 text-emerald-400" />
        )}
      </div>
      <p className="mt-2 text-3xl font-black text-white">{item.value}</p>
      <p className="mt-1 text-sm text-slate-400">
        {item.dimension} · target {item.target}
      </p>
    </FocusWrapper>
  );
}

function AlertRailCard({ item, highlightId }: { item: AlertItem; highlightId: string | null }) {
  const Icon = item.event_type.includes("sensor")
    ? Thermometer
    : item.event_type.includes("security")
      ? ShieldAlert
      : Radio;
  return (
    <FocusWrapper id={item.id} isHighlighted={item.id === highlightId} className="flex gap-4">
      <div
        className={`mt-1 rounded-xl p-3 ${
          item.priority === "HIGH" ? "bg-rose-500/15 text-rose-400" : "bg-amber-500/15 text-amber-300"
        }`}
      >
        <Icon className="h-6 w-6" />
      </div>
      <div>
        <p className="text-xs font-black tracking-[0.16em] text-slate-400 uppercase">{item.priority} · {item.location}</p>
        <p className="mt-1 text-lg font-bold text-white">{item.description}</p>
      </div>
    </FocusWrapper>
  );
}

function ExecutiveBriefView({
  visual,
  highlightId,
}: {
  visual: VisualPayload;
  highlightId: string | null;
}) {
  const kpis = kpiItems(visual);
  const alerts = alertItems(visual);
  const metrics = kpis;
  const events = alerts;
  const margin = metrics.find((item) => item.metric.toLowerCase().includes("margin"));
  const revenue = metrics.find((item) => item.metric.toLowerCase().includes("revenue"));
  if (!margin || !revenue) {
    return <p className="text-2xl font-bold text-slate-300">Waiting for the executive brief.</p>;
  }
  const rest = metrics.filter((item) => item.id !== margin?.id && item.id !== revenue?.id);
  const camera = events.find((item) => item.id === "evt_ring_001") ?? events.find((item) => item.image_url) ?? events[0];
  const otherAlerts = events.filter((item) => item.id !== camera?.id);

  return (
    <div className="grid grid-cols-12 gap-5">
      <FocusWrapper id={margin.id} isHighlighted={margin.id === highlightId} className="col-span-6 min-h-[240px]">
        <MetricChartCard
          title={`${margin.dimension} ${margin.metric}`}
          value={margin.value}
          target={margin.target}
          trend={margin.trend}
          variant="line"
          unitHint=" pts"
        />
      </FocusWrapper>
      <FocusWrapper id={revenue.id} isHighlighted={revenue.id === highlightId} className="col-span-6 min-h-[240px]">
        <MetricChartCard
          title={revenue.metric}
          value={revenue.value}
          target={revenue.target}
          trend={revenue.trend}
          variant="area"
          unitHint=" M"
        />
      </FocusWrapper>
      {rest.map((item) => (
        <div key={item.id} className="col-span-4">
          <MiniKpi item={item} highlightId={highlightId} />
        </div>
      ))}
      {camera ? (
        <FocusWrapper id={camera.id} isHighlighted={camera.id === highlightId} className="col-span-7 p-3">
          <RingCameraCard event={camera} />
        </FocusWrapper>
      ) : null}
      <div className="col-span-5 flex flex-col gap-4">
        {otherAlerts.map((item) => (
          <AlertRailCard key={item.id} item={item} highlightId={highlightId} />
        ))}
      </div>
    </div>
  );
}

function AnalysisView({
  visual,
  highlightId,
}: {
  visual: VisualPayload;
  highlightId: string | null;
}) {
  const metrics = kpiItems(visual);
  const drivers = driverItems(visual);
  const margin = metrics.find((item) => item.metric.toLowerCase().includes("margin"));
  const rows: DriverItem[] = drivers;
  if (!margin || rows.length === 0) {
    return <p className="text-2xl font-bold text-slate-300">Waiting for the metric explanation.</p>;
  }
  const barSeries = rows.map((row) => ({
    period: row.driver.replace(" Raw Material Price Bump", "").replace(" Freight Logistics ", "").slice(0, 18),
    actual: Math.abs(Number(row.impact.replace(/[^0-9.-]/g, ""))),
  }));

  return (
    <div className="grid grid-cols-12 gap-5">
      <FocusWrapper id={margin.id} isHighlighted={margin.id === highlightId} className="col-span-7 min-h-[320px]">
        <MetricChartCard
          title={`${margin.dimension} margin`}
          value={margin.value}
          target={margin.target}
          trend={margin.trend}
          variant="line"
          unitHint=" pts"
        />
      </FocusWrapper>
      <FocusWrapper id="card_primary_driver" isHighlighted={highlightId === "card_primary_driver"} className="col-span-5 min-h-[260px]">
        <MetricChartCard title="Variance contribution (pts)" value={rows[0]?.impact ?? ""} variant="bar" series={barSeries} />
      </FocusWrapper>
      <div className="col-span-7 flex flex-col gap-4">
        {rows.map((row) => (
          <FocusWrapper key={row.id} id={row.id} isHighlighted={row.id === highlightId}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-2xl font-black text-white">{row.driver}</h3>
                <p className="mt-1 text-base text-slate-300">{row.summary}</p>
              </div>
              <span className="rounded-lg bg-rose-500/15 px-3 py-1 text-xl font-black text-rose-400">{row.impact}</span>
            </div>
          </FocusWrapper>
        ))}
      </div>
    </div>
  );
}

function DecisionsView({
  visual,
  highlightId,
}: {
  visual: VisualPayload;
  highlightId: string | null;
}) {
  const items: DecisionVisualItem[] = decisionItems(visual);
  if (items.length === 0) {
    return <p className="text-2xl font-bold text-slate-300">Waiting for pending decisions.</p>;
  }
  return (
    <div className="grid grid-cols-2 gap-5">
      {items.map((item) => (
        <FocusWrapper key={item.id} id={item.id} isHighlighted={item.id === highlightId}>
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-black tracking-[0.18em] text-slate-400 uppercase">{item.category.replaceAll("_", " ")}</p>
              <h3 className="mt-1 text-2xl font-black text-white">{item.title}</h3>
            </div>
            <span className="text-2xl font-black text-white">{item.amount}</span>
          </div>
          <p className="mb-5 text-base leading-relaxed text-slate-300">{item.context_summary}</p>
          <RiskMeter riskLevel={item.risk_level} analysis={item.risk_analysis} recommendation={item.recommendation} />
        </FocusWrapper>
      ))}
    </div>
  );
}

function StepTimeline({
  title,
  steps,
  highlightId,
  blocked,
}: {
  title: string;
  steps: WorkflowStepItem[];
  highlightId: string | null;
  blocked?: boolean;
}) {
  return (
    <FocusWrapper id={steps[2]?.id ?? title} isHighlighted={steps.some((step) => step.id === highlightId)}>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <p className="text-xs font-black tracking-[0.2em] text-slate-400 uppercase">{blocked ? "Blocked pipeline" : "Active pipeline"}</p>
          <h3 className="mt-1 text-2xl font-black text-white">{title}</h3>
        </div>
        <Workflow className={blocked ? "h-7 w-7 text-rose-400" : "h-7 w-7 text-cyan-400"} />
      </div>
      <div className={`grid gap-3 ${steps.length <= 4 ? "grid-cols-4" : "grid-cols-5"}`}>
        {steps.map((step) => {
          const done = step.status === "COMPLETED";
          const current = step.status === "IN_PROGRESS";
          const blockedStep = step.status === "BLOCKED";
          return (
            <div key={step.id} id={step.id} className="text-center">
              <div
                className={`mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border-2 text-lg font-black ${
                  done
                    ? "border-emerald-400 bg-emerald-500/20 text-emerald-300"
                    : blockedStep
                      ? "border-rose-400 bg-rose-500/20 text-rose-300"
                      : current
                        ? "border-cyan-400 bg-cyan-500/20 text-cyan-200"
                        : "border-slate-700 text-slate-500"
                }`}
              >
                {step.step_number}
              </div>
              <p className="text-sm font-bold text-slate-100">{step.title}</p>
              <p className="mt-1 text-xs text-slate-400">{step.owner}</p>
              {step.blocker_reason ? (
                <p className="mt-2 text-xs font-semibold text-rose-400">{step.blocker_reason}</p>
              ) : null}
            </div>
          );
        })}
      </div>
    </FocusWrapper>
  );
}

function WorkflowView({
  visual,
  highlightId,
}: {
  visual: VisualPayload;
  highlightId: string | null;
}) {
  const live = workflowStepItems(visual);
  if (live.length === 0) {
    return <p className="text-2xl font-bold text-slate-300">Waiting for the workflow status.</p>;
  }
  const blocked = live.some((step) => step.status === "BLOCKED");
  return (
    <div className="flex flex-col gap-5">
      <StepTimeline title={visual.header_title} steps={live} highlightId={highlightId} blocked={blocked} />
    </div>
  );
}

function AuditView({
  visual,
  highlightId,
}: {
  visual: VisualPayload;
  highlightId: string | null;
}) {
  const badges = personaBadges(visual);
  const steps = protocolSteps(visual);
  const assumption = assumptionText(visual);
  if (!assumption && badges.length === 0) {
    return <p className="text-2xl font-bold text-slate-300">Waiting for the audit card.</p>;
  }
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-3 gap-4">
        {badges.map((badge) => (
          <FocusWrapper key={badge.id} id={badge.id} isHighlighted={badge.id === highlightId}>
            <p className="text-xs font-black tracking-[0.18em] text-cyan-300 uppercase">{badge.persona}</p>
            <p className="mt-2 text-lg font-bold text-white">{badge.verdict}</p>
          </FocusWrapper>
        ))}
      </div>
      <FocusWrapper id="riskiest_assumption" isHighlighted={highlightId === "riskiest_assumption"} className="border-amber-400/60 bg-amber-500/10">
        <p className="text-xs font-black tracking-[0.2em] text-amber-300 uppercase">Riskiest assumption</p>
        <p className="mt-3 text-2xl font-black text-white">{assumption}</p>
      </FocusWrapper>
      <div className="grid grid-cols-3 gap-4">
        {steps.map((step) => (
          <FocusWrapper key={step.id} id={step.id} isHighlighted={step.id === highlightId}>
            <p className="text-xs font-black tracking-[0.18em] text-slate-400 uppercase">7-day protocol</p>
            <p className="mt-2 text-lg font-bold text-white">{step.title}</p>
          </FocusWrapper>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const {
    visualState,
    voiceSummary,
    suggestedFollowups,
    tickerEvents,
    connected,
    speaking,
    pairingCode,
    runTool,
    runUtterance,
  } = useVisualState();
  const workspaceRef = useRef<HTMLDivElement>(null);
  const [tickerOpen, setTickerOpen] = useState(true);
  const [selectedView, setSelectedView] = useState<ViewId>(visualState.view_id);
  const cards = cardsFromVisual(visualState);
  const highlightId = resolveHighlight(visualState, cards);

  useEffect(() => {
    setSelectedView(visualState.view_id);
  }, [visualState.view_id]);

  const followups = suggestedFollowups.length ? suggestedFollowups : FALLBACK_PAYLOAD.voice_summary.suggested_followups;

  return (
    <div className="command-shell relative min-h-screen overflow-x-hidden px-[3.5vw] pt-[2.4vh] pb-28 text-slate-100">
      <div className="mesh-bg" />
      <header className="relative z-10 mb-5 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Building className="h-8 w-8 text-cyan-400" />
            <h1 className="font-display text-4xl font-black tracking-tight text-white">ExecuTV</h1>
            <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs font-black tracking-[0.18em] text-cyan-300 uppercase">
              Fire TV Workstation
            </span>
          </div>
          <p className="mt-1 whitespace-nowrap text-lg font-semibold text-slate-300">
            AcroCorp Global Technologies
            {pairingCode ? ` · Pair ${pairingCode}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm font-bold text-emerald-400">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-400" />
            {connected ? "Live Sync" : "Demo surface"}
          </div>
        </div>
      </header>

      <section className="relative z-10 mb-5 flex items-center gap-5 rounded-2xl border border-cyan-500/25 bg-gradient-to-r from-cyan-950/70 to-slate-900/80 p-5 shadow-2xl backdrop-blur-xl">
        <div className="rounded-xl bg-cyan-500/15 p-3 text-cyan-300">
          <AudioLines className="h-8 w-8" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-3">
            <span className="text-xs font-black tracking-[0.22em] text-cyan-300 uppercase">Alexa+ Narration</span>
            <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] font-bold tracking-widest text-slate-400 uppercase">
              {screenLabel(selectedView)}
            </span>
          </div>
          <p className="text-lg leading-snug font-semibold text-white">{voiceSummary}</p>
        </div>
        <VoiceWaveform active={speaking} />
      </section>

      <div className="relative z-10 mb-5 flex flex-wrap items-center gap-3">
        {SCREEN_TOOLS.map((screen) => {
          const active = selectedView === screen.id;
          return (
            <button
              key={screen.id}
              type="button"
              onClick={() => {
                setSelectedView(screen.id);
                void runTool(screen.tool, screen.args);
              }}
              className={`rounded-full px-5 py-2 text-sm font-black tracking-wide uppercase transition ${
                active
                  ? "bg-cyan-400 text-slate-950 shadow-[0_0_20px_rgba(0,229,255,0.35)]"
                  : "border border-slate-700 bg-slate-900/70 text-slate-300 hover:border-slate-500"
              }`}
            >
              {screen.label}
            </button>
          );
        })}
        <span className="mx-2 h-6 w-px bg-slate-700" />
        {JUDGE_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => void runUtterance(prompt)}
            className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-4 py-2 text-sm font-semibold text-cyan-200 hover:border-cyan-400/50"
          >
            <Sparkles className="mr-2 inline h-4 w-4" />
            {prompt}
          </button>
        ))}
        {followups.slice(0, 2).map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => void runUtterance(prompt)}
            className="rounded-full border border-slate-700 bg-slate-900/60 px-4 py-2 text-sm text-slate-300"
          >
            {prompt}
          </button>
        ))}
      </div>

      <TvFocusRoot highlightId={highlightId} scopeRef={workspaceRef}>
        <div className="relative z-10 flex min-h-0 gap-5" ref={workspaceRef}>
          <main className="min-w-0 flex-1">
            <AnimatePresence mode="wait">
              <motion.div
                key={String(selectedView)}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.28 }}
              >
                {selectedView === "AUDIT_SCORECARD" ? (
                  <AuditView visual={visualState} highlightId={highlightId} />
                ) : selectedView === "ANALYSIS_DEEP_DIVE" ? (
                  <AnalysisView visual={visualState} highlightId={highlightId} />
                ) : selectedView === "DECISIONS_LIST" ? (
                  <DecisionsView visual={visualState} highlightId={highlightId} />
                ) : selectedView === "WORKFLOW_TRACKER" ? (
                  <WorkflowView visual={visualState} highlightId={highlightId} />
                ) : (
                  <ExecutiveBriefView visual={visualState} highlightId={highlightId} />
                )}
              </motion.div>
            </AnimatePresence>
          </main>
          <TickerSidebar events={tickerEvents} collapsed={!tickerOpen} onToggle={() => setTickerOpen((open) => !open)} />
        </div>
      </TvFocusRoot>

      <footer className="remote-legend">
        <span>[▲▼◄►] Navigate</span>
        <span className="opacity-40">|</span>
        <span>[OK] Inspect</span>
        <span className="opacity-40">|</span>
        <span className="flex items-center gap-1">
          <MicVocal className="h-4 w-4 text-cyan-300" />
          Alexa Voice
        </span>
      </footer>
    </div>
  );
}
