import type { DecisionVisualItem, RiskAnalysis, RiskLevel } from "../types/visual";

type RiskMeterProps = {
  riskLevel: RiskLevel;
  analysis?: RiskAnalysis;
  recommendation?: string;
};

function gaugePercent(level: RiskLevel): number {
  const token = String(level).toUpperCase();
  if (token === "HIGH") {
    return 88;
  }
  if (token === "MEDIUM") {
    return 58;
  }
  return 26;
}

function gaugeColor(level: RiskLevel): string {
  const token = String(level).toUpperCase();
  if (token === "HIGH") {
    return "#FB7185";
  }
  if (token === "MEDIUM") {
    return "#FBBF24";
  }
  return "#34D399";
}

export function RiskMeter({ riskLevel, analysis, recommendation }: RiskMeterProps) {
  const percent = gaugePercent(riskLevel);
  const color = gaugeColor(riskLevel);
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - percent / 100);
  const financial = analysis?.financial_risk ?? riskLevel;
  const legal = analysis?.legal_compliance ?? analysis?.legal_flag ?? analysis?.budget_status ?? analysis?.urgency ?? "Pending review";

  return (
    <div className="flex items-center gap-5">
      <svg viewBox="0 0 108 108" className="h-24 w-24 shrink-0">
        <circle cx="54" cy="54" r={radius} fill="none" stroke="rgba(148,163,184,0.18)" strokeWidth="10" />
        <circle
          cx="54"
          cy="54"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 54 54)"
          className="drop-shadow-[0_0_10px_rgba(0,229,255,0.25)]"
        />
        <text x="54" y="50" textAnchor="middle" className="fill-white text-[13px] font-black">
          {String(riskLevel).toUpperCase()}
        </text>
        <text x="54" y="68" textAnchor="middle" className="fill-slate-400 text-[9px] font-bold tracking-widest">
          RISK
        </text>
      </svg>
      <div className="min-w-0 space-y-1.5">
        <p className="text-[11px] font-black tracking-[0.18em] text-slate-400 uppercase">AI Legal & Financial Gauge</p>
        <p className="text-sm text-slate-200">
          Financial: <span className="font-bold text-white">{financial}</span>
        </p>
        <p className="truncate text-sm text-slate-300">{legal}</p>
        {recommendation ? (
          <span
            className={`inline-flex rounded-full px-2.5 py-0.5 text-[11px] font-black tracking-widest uppercase ${
              recommendation === "APPROVE"
                ? "bg-emerald-500/15 text-emerald-400"
                : recommendation === "ESCALATE"
                  ? "bg-rose-500/15 text-rose-400"
                  : "bg-amber-500/15 text-amber-300"
            }`}
          >
            {recommendation}
          </span>
        ) : null}
      </div>
    </div>
  );
}

export function riskFromDecision(item: DecisionVisualItem): RiskMeterProps {
  return {
    riskLevel: item.risk_level,
    analysis: item.risk_analysis,
    recommendation: item.recommendation,
  };
}
