import { useCallback, useEffect, useRef, useState } from "react";

import {
  CORE_ENGINE_URL,
  FALLBACK_PAYLOAD,
  INGRESS_GATEWAY_URL,
  asDualPayload,
  asTickerEvent,
  type DualPayload,
  type TickerEvent,
} from "../types/visual";

const READ_TOOLS = new Set([
  "get_executive_brief",
  "explain_metric_change",
  "get_pending_decisions",
  "start_workflow",
  "get_workflow_status",
  "get_recent_events",
]);

type SpeechHandlers = { onStart?: () => void; onEnd?: () => void };

function isLocalPage(): boolean {
  if (typeof window === "undefined") {
    return true;
  }
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1" || host === "[::1]";
}

function engineBases(): string[] {
  if (!isLocalPage()) {
    return [window.location.origin];
  }
  return [...new Set(["http://localhost:8001", "http://127.0.0.1:8001", CORE_ENGINE_URL])];
}

function ingressBases(): string[] {
  if (!isLocalPage()) {
    return [window.location.origin];
  }
  return [...new Set([INGRESS_GATEWAY_URL, "http://127.0.0.1:8000", "http://localhost:8000"])];
}

let speechGeneration = 0;
let pendingSpeech: (() => void) | null = null;
let speechUnlockBound = false;

function bindSpeechUnlock(): void {
  if (speechUnlockBound || typeof window === "undefined") {
    return;
  }
  speechUnlockBound = true;
  const kick = () => pendingSpeech?.();
  window.addEventListener("pointerdown", kick);
  window.addEventListener("keydown", kick);
}

export function triggerTTS(text: string, handlers?: SpeechHandlers): void {
  if (!text.trim() || typeof window === "undefined" || !window.speechSynthesis) {
    handlers?.onEnd?.();
    return;
  }
  const generation = ++speechGeneration;
  const synth = window.speechSynthesis;
  let started = false;
  let queued = false;
  let finished = false;

  const finish = () => {
    if (finished || generation !== speechGeneration) {
      return;
    }
    finished = true;
    if (pendingSpeech) {
      pendingSpeech = null;
    }
    handlers?.onEnd?.();
  };

  const utter = () => {
    if (generation !== speechGeneration || started || queued) {
      return;
    }
    queued = true;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.02;
    utterance.pitch = 0.96;
    const voice = synth.getVoices().find((item) => item.lang.toLowerCase().startsWith("en"));
    if (voice) {
      utterance.voice = voice;
    }
    utterance.onstart = () => {
      if (generation !== speechGeneration) {
        return;
      }
      started = true;
      pendingSpeech = null;
      handlers?.onStart?.();
    };
    utterance.onend = finish;
    utterance.onerror = (event) => {
      queued = false;
      if (event.error === "interrupted" || event.error === "canceled" || event.error === "not-allowed") {
        return;
      }
      finish();
    };
    synth.resume();
    synth.speak(utterance);
  };

  pendingSpeech = () => {
    if (started || generation !== speechGeneration) {
      return;
    }
    queued = false;
    synth.resume();
    utter();
  };
  bindSpeechUnlock();

  let planned = false;
  const run = () => {
    if (planned || generation !== speechGeneration || started) {
      return;
    }
    planned = true;
    if (synth.speaking || synth.pending) {
      synth.cancel();
    }
    window.setTimeout(utter, 100);
  };

  if (synth.getVoices().length === 0) {
    synth.addEventListener("voiceschanged", run, { once: true });
    window.setTimeout(run, 250);
  } else {
    run();
  }
}

async function fetchJson(url: string, init?: RequestInit): Promise<unknown> {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }
  return response.json();
}

async function loadDualPayload(path: string, init?: RequestInit): Promise<DualPayload | null> {
  let legacy: DualPayload | null = null;
  for (const base of engineBases()) {
    try {
      const raw = await fetchJson(`${base}${path}`, init);
      const data = asDualPayload(raw);
      if (!data) {
        continue;
      }
      const root = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
      const body = (root.payloads && typeof root.payloads === "object" ? root.payloads : root) as Record<
        string,
        unknown
      >;
      if (body.visual_state_model) {
        return data;
      }
      legacy = data;
    } catch {
      // Windows can bind localhost and 127.0.0.1 to different listeners.
    }
  }
  return legacy;
}

function samePayload(left: DualPayload, right: DualPayload): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

export function useVisualState() {
  const [payload, setPayload] = useState<DualPayload>(FALLBACK_PAYLOAD);
  const [tickerEvents, setTickerEvents] = useState<TickerEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [pairingCode, setPairingCode] = useState("");
  const seenTicks = useRef(new Set<string>());
  const lastSpoken = useRef("");

  const speakNarration = useCallback((text: string) => {
    if (!text || text === lastSpoken.current) {
      return;
    }
    triggerTTS(text, {
      onStart: () => {
        lastSpoken.current = text;
        setSpeaking(true);
      },
      onEnd: () => setSpeaking(false),
    });
  }, []);

  const applyDualPayload = useCallback(
    (next: DualPayload, { speak = true }: { speak?: boolean } = {}) => {
      setPayload((current) => (samePayload(current, next) ? current : next));
      setConnected(true);
      if (speak) {
        speakNarration(next.voice_summary.narration_text);
      }
    },
    [speakNarration],
  );

  const fetchCurrentState = useCallback(async () => {
    try {
      const data = await loadDualPayload("/v1/briefings/current");
      if (data) {
        applyDualPayload(data, { speak: lastSpoken.current === "" });
      }
    } catch {
      setConnected(false);
    }
  }, [applyDualPayload]);

  const fetchToolState = useCallback(
    async (toolName: string, args: Record<string, unknown> = {}, speak = true) => {
      const name = toolName;
      if (name !== "execute_decision" && !READ_TOOLS.has(name)) {
        await fetchCurrentState();
        return;
      }
      try {
        const data = await loadDualPayload("/api/v1/orchestrate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            transaction_id: `tv_${Date.now()}`,
            tool_name: name,
            session_context: { org_id: "org_acme_corp" },
            parameters: args,
          }),
        });
        if (data) {
          applyDualPayload(data, { speak });
        }
      } catch {
        await fetchCurrentState();
      }
    },
    [applyDualPayload, fetchCurrentState],
  );

  const runUtterance = useCallback(
    async (utterance: string) => {
      try {
        const data = await loadDualPayload("/api/v1/reason", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            utterance,
            org_id: "org_acme_corp",
            execute: true,
          }),
        });
        if (data) {
          applyDualPayload(data, { speak: true });
          return;
        }
      } catch {
        // Fall through to keyword routing.
      }
      const lower = utterance.toLowerCase();
      if (lower.includes("spot") && (lower.includes("approv") || lower.includes("confirm"))) {
        await fetchToolState("execute_decision", {
          decision_id: "dec_004",
          choice: "approve",
          session_id: "tv-local",
        });
        return;
      }
      if (lower.includes("month-end") || lower.includes("month end") || lower.includes("close blocked")) {
        await fetchToolState("get_workflow_status", { workflow_name: "month-end close" });
        return;
      }
      if (lower.includes("margin") || lower.includes("region b")) {
        await fetchToolState("explain_metric_change", {
          metric_name: "margin",
          dimension: "Region B",
          window: "Q3-2026",
        });
        return;
      }
      if (lower.includes("decision") || lower.includes("need me") || lower.includes("contract")) {
        await fetchToolState("get_pending_decisions");
        return;
      }
      if (lower.includes("ring") || lower.includes("warehouse") || lower.includes("camera")) {
        await fetchToolState("get_recent_events", { limit: 5 });
        return;
      }
      if (lower.includes("workflow") || lower.includes("rfq") || lower.includes("12345")) {
        await fetchToolState("start_workflow", { workflow_name: "12345" });
        return;
      }
      await fetchToolState("get_executive_brief");
    },
    [applyDualPayload, fetchToolState],
  );

  const fetchCurrentStateRef = useRef(fetchCurrentState);
  const fetchToolStateRef = useRef(fetchToolState);
  fetchCurrentStateRef.current = fetchCurrentState;
  fetchToolStateRef.current = fetchToolState;

  useEffect(() => {
    void fetchCurrentStateRef.current();
    let cancelled = false;
    const sources: EventSource[] = [];

    const onFrame = (message: MessageEvent<string>) => {
      try {
        const raw = JSON.parse(message.data) as Record<string, unknown>;
        if (raw.type === "snapshot" && Array.isArray(raw.events)) {
          const events = raw.events
            .map(asTickerEvent)
            .filter((item): item is TickerEvent => item != null)
            .slice(0, 12);
          for (const event of events) {
            seenTicks.current.add(`${event.tool_name}:${event.status}:${event.timestamp}`);
          }
          setTickerEvents(events);
          return;
        }
        const event = asTickerEvent(raw.event ?? raw);
        if (!event) {
          return;
        }
        const tickId = `${event.tool_name}:${event.status}:${event.timestamp}`;
        if (seenTicks.current.has(tickId)) {
          return;
        }
        seenTicks.current.add(tickId);
        setTickerEvents((current) => [event, ...current].slice(0, 12));
        const embedded = asDualPayload(raw.visual_state_model ? { visual_state_model: raw.visual_state_model, voice_summary: raw.voice_summary } : null);
        if (embedded) {
          applyDualPayload(embedded, { speak: false });
        } else if (event.status === "COMPLETED" && event.tool_name !== "execute_decision") {
          void fetchToolStateRef.current(event.tool_name, event.args, true);
        }
      } catch {
        // Keep the 10-foot surface up if a ticker frame is malformed.
      }
    };

    const timers: number[] = [];

    const connectUrl = (url: string, attempt = 0) => {
      if (cancelled) {
        return;
      }
      const next = new EventSource(url);
      sources.push(next);
      let opened = false;
      next.addEventListener("ticker", onFrame);
      next.onmessage = onFrame;
      next.onopen = () => {
        opened = true;
        setConnected(true);
        void fetchCurrentStateRef.current();
      };
      next.onerror = () => {
        next.close();
        const index = sources.indexOf(next);
        if (index >= 0) {
          sources.splice(index, 1);
        }
        if (cancelled) {
          return;
        }
        if (!opened && attempt === 0) {
          const base = ingressBases().find((candidate) => !url.startsWith(candidate));
          if (base) {
            const path = url.slice(url.indexOf("/events/ticker"));
            connectUrl(`${base}${path}`, attempt + 1);
            return;
          }
        }
        setConnected(false);
        const wait = Math.min(1000 * 2 ** Math.min(attempt, 4), 15000);
        timers.push(window.setTimeout(() => connectUrl(url, attempt + 1), wait));
      };
    };

    const boot = async () => {
      const bases = ingressBases();
      let base = bases[0];
      let pairing = "";
      for (const candidate of bases) {
        try {
          const raw = await fetchJson(`${candidate}/displays/pairing-code`);
          const code = (raw as { pairing_code?: string }).pairing_code;
          if (code) {
            base = candidate;
            pairing = code;
            setPairingCode(code);
            break;
          }
        } catch {
          // Try the next ingress base.
        }
      }
      connectUrl(`${base}/events/ticker`);
      if (pairing) {
        connectUrl(`${base}/events/ticker/${pairing}`);
      }
    };

    void boot();
    return () => {
      cancelled = true;
      for (const timer of timers) {
        window.clearTimeout(timer);
      }
      for (const source of sources) {
        source.onmessage = null;
        source.removeEventListener("ticker", onFrame);
        source.close();
      }
      window.speechSynthesis?.cancel();
    };
  }, []);

  const visual = payload.visual_state_model;
  return {
    visualState: visual,
    voiceSummary: payload.voice_summary.narration_text,
    suggestedFollowups: payload.voice_summary.suggested_followups,
    tickerEvents,
    activeHighlightId: visual.highlight_target_id ?? null,
    connected,
    speaking,
    pairingCode,
    triggerTTS,
    applyDualPayload,
    refreshState: fetchCurrentState,
    runTool: fetchToolState,
    runUtterance,
  };
}
