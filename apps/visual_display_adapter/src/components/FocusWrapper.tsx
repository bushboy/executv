import { useEffect, useRef, type KeyboardEvent, type ReactNode, type RefObject } from "react";

type FocusWrapperProps = {
  id: string;
  isHighlighted?: boolean;
  children: ReactNode;
  className?: string;
};

function playRemoteClick() {
  if (typeof window === "undefined") {
    return;
  }
  const AudioCtx = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AudioCtx) {
    return;
  }
  const ctx = new AudioCtx();
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  oscillator.type = "triangle";
  oscillator.frequency.value = 920;
  gain.gain.value = 0.035;
  oscillator.connect(gain).connect(ctx.destination);
  oscillator.start();
  gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.07);
  oscillator.stop(ctx.currentTime + 0.08);
  oscillator.onended = () => void ctx.close();
}

export function FocusWrapper({
  id,
  isHighlighted = false,
  children,
  className = "",
}: FocusWrapperProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = cardRef.current;
    if (!isHighlighted || node == null || document.activeElement === node) {
      return;
    }
    node.scrollIntoView({ behavior: "smooth", block: "nearest" });
    node.focus({ preventScroll: true });
  }, [isHighlighted]);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }
    event.preventDefault();
    event.currentTarget.click();
  }

  return (
    <div
      ref={cardRef}
      id={id}
      tabIndex={0}
      onKeyDown={onKeyDown}
      className={`focus-tile group relative rounded-2xl p-6 backdrop-blur-xl shadow-2xl transition-all duration-300 ${
        isHighlighted
          ? "scale-[1.02] border border-[#00E5FF] bg-slate-900/80 ring-4 ring-[#00E5FF] shadow-[0_0_40px_rgba(0,229,255,0.35)]"
          : "border border-slate-800/80 bg-slate-900/80 hover:border-slate-700/80"
      } ${className}`}
    >
      {isHighlighted ? (
        <span className="absolute -top-3 right-5 rounded-full bg-[#00E5FF] px-3 py-1 text-[11px] font-black tracking-[0.18em] text-slate-950 uppercase shadow-[0_0_18px_rgba(0,229,255,0.8)]">
          Voice Focus
        </span>
      ) : null}
      {children}
    </div>
  );
}

type TvFocusRootProps = {
  highlightId: string | null;
  scopeRef: RefObject<HTMLElement | null>;
  children: ReactNode;
};

export function TvFocusRoot({ highlightId, scopeRef, children }: TvFocusRootProps) {
  useEffect(() => {
    const root = scopeRef.current;
    if (root == null) {
      return;
    }
    const highlighted = highlightId ? root.querySelector<HTMLElement>(`#${CSS.escape(highlightId)}`) : null;
    const next = highlighted ?? root.querySelector<HTMLElement>("[tabindex='0']");
    if (next == null || document.activeElement === next) {
      return;
    }
    next.focus({ preventScroll: true });
  }, [highlightId, scopeRef]);

  useEffect(() => {
    const root = scopeRef.current;
    if (root == null) {
      return;
    }
    const tilesRoot = root;

    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (!["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) {
        return;
      }
      const tiles = [...tilesRoot.querySelectorAll<HTMLElement>("[tabindex='0']")];
      if (tiles.length === 0) {
        return;
      }
      const active = document.activeElement;
      const index = active instanceof HTMLElement ? tiles.indexOf(active) : -1;
      const delta = event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 1;
      const next = tiles[(index + delta + tiles.length) % tiles.length];
      event.preventDefault();
      playRemoteClick();
      next.focus();
    }

    tilesRoot.addEventListener("keydown", onKeyDown);
    return () => tilesRoot.removeEventListener("keydown", onKeyDown);
  }, [scopeRef]);

  return children;
}
