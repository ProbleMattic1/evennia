"use client";

import { useEffect, useMemo, useRef } from "react";

import { HitekGameLogChrome } from "@/components/hitek-game-log-chrome";
import type { MsgStreamEntry } from "@/lib/ui-api";

type Props = {
  messages: MsgStreamEntry[];
  compact?: boolean;
};

function streamTag(meta: MsgStreamEntry["meta"]): string | null {
  const parts: string[] = [];
  if (meta.surface) parts.push(String(meta.surface));
  if (meta.interactionKey) parts.push(String(meta.interactionKey));
  if (parts.length === 0) return null;
  return `[${parts.join(":")}]`;
}

/** Row + HTML body inherit one phosphor hue per stream (server `meta.eventType` / billboard severity). */
function feedRowClass(meta: MsgStreamEntry["meta"]): string {
  const inherit = "[&_*]:text-inherit";
  if (meta.billboardSeverity === "alert") {
    return `text-red-300 [text-shadow:0_0_12px_rgba(248,113,113,0.55)] ${inherit}`;
  }
  if (meta.billboardSeverity === "warn") {
    return `text-orange-300 [text-shadow:0_0_10px_rgba(251,146,60,0.5)] ${inherit}`;
  }
  if (meta.eventType === "travel") {
    return `text-amber-200 [text-shadow:0_0_11px_rgba(252,211,77,0.45)] ${inherit}`;
  }
  if (meta.eventType === "interaction") {
    return `text-fuchsia-300 [text-shadow:0_0_11px_rgba(232,121,249,0.42)] ${inherit}`;
  }
  /* Default room / narrative “emit” stream — classic green phosphor + faint RGB fringe */
  return `text-emerald-400 [text-shadow:0_0_10px_rgba(52,211,153,0.42),-0.4px_0_0_rgba(220,255,235,0.35),0.4px_0_0_rgba(100,255,160,0.3)] ${inherit}`;
}

function feedTagClass(meta: MsgStreamEntry["meta"]): string {
  if (meta.billboardSeverity === "alert") return "text-red-400/85";
  if (meta.billboardSeverity === "warn") return "text-orange-400/85";
  if (meta.eventType === "travel") return "text-amber-400/80";
  if (meta.eventType === "interaction") return "text-fuchsia-400/80";
  return "text-emerald-500/80";
}

export function GameLogPanel({ messages, compact }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  const newestFirst = useMemo(() => [...messages].reverse(), [messages]);

  useEffect(() => {
    containerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [messages]);

  const emptyClass = compact
    ? "min-h-[72px] bg-zinc-950/95 pl-2.5 pr-1.5 pt-1.5 pb-1.5 font-mono text-xs leading-snug text-emerald-500/70 [text-shadow:0_0_12px_rgba(52,211,153,0.35),0_1px_2px_rgba(0,0,0,0.95)]"
    : "min-h-[120px] bg-zinc-950/95 p-2 pl-3 font-mono text-xs leading-5 text-emerald-500/70 [text-shadow:0_0_14px_rgba(52,211,153,0.38),0_1px_2px_rgba(0,0,0,0.95)]";

  const listClass = compact
    ? "max-h-[min(200px,35vh)] min-h-[72px] overflow-y-auto bg-zinc-950/95 pl-2.5 pr-1.5 pt-1.5 pb-1.5 font-mono text-xs leading-snug [scrollbar-color:rgba(52,211,153,0.45)_rgba(0,0,0,0.4)]"
    : "max-h-[min(320px,50vh)] min-h-[120px] overflow-y-auto bg-zinc-950/95 p-2 pl-3 font-mono text-xs leading-5 [scrollbar-color:rgba(52,211,153,0.45)_rgba(0,0,0,0.4)]";

  if (messages.length === 0) {
    return (
      <HitekGameLogChrome compact={compact}>
        <div className={emptyClass}>Waiting for game output…</div>
      </HitekGameLogChrome>
    );
  }

  return (
    <HitekGameLogChrome compact={compact}>
      <div ref={containerRef} className={listClass}>
        {newestFirst.map((msg) => {
          const tag = streamTag(msg.meta);
          return (
            <div key={msg.seq} className={`mb-1 break-words ${feedRowClass(msg.meta)}`}>
              {tag ? (
                <span className={`mr-1 font-mono text-[10px] font-semibold uppercase tracking-wide ${feedTagClass(msg.meta)}`}>
                  {tag}
                </span>
              ) : null}
              <span dangerouslySetInnerHTML={{ __html: msg.html }} />
            </div>
          );
        })}
      </div>
    </HitekGameLogChrome>
  );
}
