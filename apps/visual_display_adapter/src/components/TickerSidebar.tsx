import { Activity, PanelRightClose, PanelRightOpen } from "lucide-react";

import type { TickerEvent } from "../types/visual";

type TickerSidebarProps = {
  events: TickerEvent[];
  collapsed: boolean;
  onToggle: () => void;
};

function statusClass(status: string): string {
  if (status === "COMPLETED") {
    return "bg-emerald-500/20 text-emerald-400";
  }
  if (status === "EXECUTING") {
    return "bg-amber-500/20 text-amber-300";
  }
  return "bg-rose-500/20 text-rose-400";
}

export function TickerSidebar({ events, collapsed, onToggle }: TickerSidebarProps) {
  if (collapsed) {
    return (
      <button
        type="button"
        onClick={onToggle}
        className="flex h-full w-16 flex-col items-center gap-3 rounded-2xl border border-slate-800/80 bg-slate-900/80 px-2 py-5 backdrop-blur-xl"
        aria-label="Open MCP ticker"
      >
        <PanelRightOpen className="h-5 w-5 text-cyan-400" />
        <span className="rotate-180 text-[11px] font-black tracking-[0.2em] text-slate-400 uppercase [writing-mode:vertical-rl]">
          MCP Ticker
        </span>
      </button>
    );
  }

  return (
    <aside className="flex h-[min(72vh,760px)] min-h-0 w-[300px] shrink-0 flex-col rounded-2xl border border-slate-800/80 bg-slate-950/80 p-5 shadow-2xl backdrop-blur-xl">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-xs font-black tracking-[0.22em] text-slate-300 uppercase">
          <Activity className="h-4 w-4 text-cyan-400" />
          Live MCP Inspector
        </h2>
        <button
          type="button"
          onClick={onToggle}
          className="rounded-lg border border-slate-700 p-1.5 text-slate-400 hover:text-white"
          aria-label="Collapse MCP ticker"
        >
          <PanelRightClose className="h-4 w-4" />
        </button>
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {events.length > 0 ? (
          events.map((event, index) => (
            <article
              key={`${event.tool_name}-${event.timestamp}-${index}`}
              className="rounded-xl border border-slate-800 bg-slate-950/90 p-3 font-mono text-xs"
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="truncate font-semibold text-cyan-300">{event.tool_name}</span>
                <span className={`rounded px-1.5 py-0.5 text-[10px] font-black tracking-wide ${statusClass(String(event.status))}`}>
                  {event.status}
                </span>
              </div>
              <pre className="overflow-x-auto text-[10px] leading-relaxed text-slate-400">
                {JSON.stringify(event.args, null, 2)}
              </pre>
              <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500">
                <span>{event.detail || "json-rpc"}</span>
                <span>{event.latency_ms > 0 ? `${event.latency_ms}ms` : "pending"}</span>
              </div>
            </article>
          ))
        ) : (
          <p className="py-10 text-center text-xs text-slate-500 italic">Awaiting MCP tool invocations…</p>
        )}
      </div>
    </aside>
  );
}
