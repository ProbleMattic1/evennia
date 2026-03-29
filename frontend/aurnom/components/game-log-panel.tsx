"use client";

import { useEffect, useMemo, useRef } from "react";
import type { MsgStreamEntry } from "@/lib/ui-api";

type Props = {
  messages: MsgStreamEntry[];
  compact?: boolean;
};

export function GameLogPanel({ messages, compact }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  const newestFirst = useMemo(
    () => [...messages].reverse(),
    [messages],
  );

  useEffect(() => {
    containerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [messages]);

  const emptyClass = compact
    ? "min-h-[72px] border border-cyan-900/40 bg-zinc-950/80 p-1.5 font-mono text-[10px] leading-snug text-ui-muted"
    : "min-h-[120px] border border-cyan-900/40 bg-zinc-950/80 p-2 font-mono text-[11px] leading-5 text-ui-muted";

  const listClass = compact
    ? "max-h-[min(200px,35vh)] min-h-[72px] overflow-y-auto border border-cyan-900/40 bg-zinc-950/80 p-1.5 font-mono text-[10px] leading-snug text-zinc-200"
    : "max-h-[min(320px,50vh)] min-h-[120px] overflow-y-auto border border-cyan-900/40 bg-zinc-950/80 p-2 font-mono text-[11px] leading-5 text-zinc-200";

  if (messages.length === 0) {
    return <div className={emptyClass}>Waiting for game output…</div>;
  }

  return (
    <div ref={containerRef} className={listClass}>
      {newestFirst.map((msg) => (
        <div
          key={msg.seq}
          className="mb-1 break-words"
          dangerouslySetInnerHTML={{ __html: msg.html }}
        />
      ))}
    </div>
  );
}
