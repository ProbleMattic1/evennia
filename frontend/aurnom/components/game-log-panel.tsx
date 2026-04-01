"use client";

import { useEffect, useMemo, useRef } from "react";
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

export function GameLogPanel({ messages, compact }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  const newestFirst = useMemo(() => [...messages].reverse(), [messages]);

  useEffect(() => {
    containerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [messages]);

  const emptyClass = compact
    ? "min-h-[72px] border border-cyan-900/40 bg-zinc-950/80 p-1.5 font-mono text-xs leading-snug text-ui-muted"
    : "min-h-[120px] border border-cyan-900/40 bg-zinc-950/80 p-2 font-mono text-xs leading-5 text-ui-muted";

  const listClass = compact
    ? "max-h-[min(200px,35vh)] min-h-[72px] overflow-y-auto border border-cyan-900/40 bg-zinc-950/80 p-1.5 font-mono text-xs leading-snug text-ui-soft"
    : "max-h-[min(320px,50vh)] min-h-[120px] overflow-y-auto border border-cyan-900/40 bg-zinc-950/80 p-2 font-mono text-xs leading-5 text-ui-soft";

  if (messages.length === 0) {
    return <div className={emptyClass}>Waiting for game output…</div>;
  }

  return (
    <div ref={containerRef} className={listClass}>
      {newestFirst.map((msg) => {
        const tag = streamTag(msg.meta);
        return (
          <div key={msg.seq} className="mb-1 break-words">
            {tag ? <span className="mr-1 font-mono text-[10px] text-ui-muted">{tag}</span> : null}
            <span dangerouslySetInnerHTML={{ __html: msg.html }} />
          </div>
        );
      })}
    </div>
  );
}
