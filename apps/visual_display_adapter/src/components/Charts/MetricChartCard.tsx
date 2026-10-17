import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { parseMetricNumber } from "../../types/visual";

type ChartVariant = "area" | "line" | "bar";

export type ChartPoint = {
  period: string;
  actual: number;
  target?: number;
};

type MetricChartCardProps = {
  title: string;
  value: string;
  target?: string;
  trend?: string;
  variant?: ChartVariant;
  series?: ChartPoint[];
  unitHint?: string;
};

const PERIODS = ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "Now"];

function buildTrend(current: number, target: number): ChartPoint[] {
  return PERIODS.map((period, index) => {
    const t = index / (PERIODS.length - 1);
    const drift = target + (current - target) * (0.12 + 0.88 * t * t);
    const noise = Math.sin(index * 1.15) * Math.abs(target - current) * 0.045;
    return {
      period,
      actual: Number((drift + noise).toFixed(2)),
      target: Number(target.toFixed(2)),
    };
  });
}

function trendColor(trend?: string): { stroke: string } {
  const token = (trend ?? "").toUpperCase();
  if (token === "DOWN" || token === "HIGH") {
    return { stroke: "#FB7185" };
  }
  if (token === "UP") {
    return { stroke: "#34D399" };
  }
  return { stroke: "#00E5FF" };
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value?: number; name?: string; color?: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) {
    return null;
  }
  return (
    <div className="rounded-xl border border-slate-700/80 bg-slate-950/95 px-3 py-2 text-sm text-slate-100 shadow-2xl">
      <p className="mb-1 text-[11px] font-bold tracking-widest text-slate-400 uppercase">{label}</p>
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color }} className="font-semibold">
          {entry.name}: {entry.value}
        </p>
      ))}
    </div>
  );
}

export function MetricChartCard({
  title,
  value,
  target,
  trend,
  variant = "area",
  series,
  unitHint,
}: MetricChartCardProps) {
  const current = parseMetricNumber(value);
  const goal = parseMetricNumber(target) || current;
  const data = series ?? buildTrend(current, goal);
  const colors = trendColor(trend);
  const min = Math.min(...data.map((point) => Math.min(point.actual, point.target ?? point.actual)));
  const max = Math.max(...data.map((point) => Math.max(point.actual, point.target ?? point.actual)));
  const pad = Math.max((max - min) * 0.22, Math.abs(max) * 0.02, 0.4);
  const domain: [number, number] = [Number((min - pad).toFixed(2)), Number((max + pad).toFixed(2))];
  const fillId = `fill-${title.replace(/[^a-z0-9]/gi, "").toLowerCase() || "metric"}`;
  const delta = current - goal;
  const deltaLabel = `${delta >= 0 ? "+" : ""}${delta.toFixed(1)}${unitHint ?? ""}`;

  return (
    <div className="flex h-full min-h-[220px] flex-col">
      <div className="mb-3 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold tracking-[0.22em] text-slate-400 uppercase">{title}</p>
          <p className="mt-1 text-3xl font-black tracking-tight text-white xl:text-4xl">{value}</p>
        </div>
        <div className="text-right">
          {target ? <p className="text-sm font-semibold text-emerald-400">Target {target}</p> : null}
          {target ? (
            <p className={`text-sm font-bold ${delta < 0 ? "text-rose-400" : "text-emerald-400"}`}>{deltaLabel}</p>
          ) : null}
        </div>
      </div>
      <div className="min-h-[140px] flex-1">
        <ResponsiveContainer width="100%" height="100%">
          {variant === "line" ? (
            <LineChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis dataKey="period" tick={{ fill: "#94A3B8", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis
                domain={domain}
                tickFormatter={(tick: number) => (Math.abs(tick) >= 100 ? tick.toFixed(0) : tick.toFixed(1))}
                tick={{ fill: "#64748B", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={52}
              />
              <Tooltip content={<ChartTooltip />} />
              <Line type="monotone" dataKey="target" stroke="#34D399" strokeDasharray="5 5" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="actual" stroke={colors.stroke} strokeWidth={3} dot={{ r: 3, fill: colors.stroke }} />
            </LineChart>
          ) : variant === "bar" ? (
            <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis dataKey="period" tick={{ fill: "#94A3B8", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis
                domain={domain}
                tickFormatter={(tick: number) => (Math.abs(tick) >= 100 ? tick.toFixed(0) : tick.toFixed(1))}
                tick={{ fill: "#64748B", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={52}
              />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="actual" fill={colors.stroke} radius={[8, 8, 0, 0]} />
            </BarChart>
          ) : (
            <AreaChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors.stroke} stopOpacity={0.45} />
                  <stop offset="95%" stopColor={colors.stroke} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis dataKey="period" tick={{ fill: "#94A3B8", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis
                domain={domain}
                tickFormatter={(tick: number) => (Math.abs(tick) >= 100 ? tick.toFixed(0) : tick.toFixed(1))}
                tick={{ fill: "#64748B", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={52}
              />
              <Tooltip content={<ChartTooltip />} />
              <Area type="monotone" dataKey="target" stroke="#34D399" strokeDasharray="6 6" fill="none" strokeWidth={2} />
              <Area type="monotone" dataKey="actual" stroke={colors.stroke} fill={`url(#${fillId})`} strokeWidth={3} />
            </AreaChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
