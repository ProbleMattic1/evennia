"use client";

import { useEffect, useRef } from "react";
import type { MsgStreamEntry } from "@/lib/ui-api";

type Props = {
  messages: MsgStreamEntry[];
  compact?: boolean;
};

export function GameLogPanel({ messages, compact }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const emptyClass = compact
    ? "min-h-[72px] border border-cyan-900/40 bg-zinc-950/80 p-1.5 font-mono text-[10px] leading-snug text-zinc-500"
    : "min-h-[120px] border border-cyan-900/40 bg-zinc-950/80 p-2 font-mono text-[11px] leading-5 text-zinc-500";

  const listClass = compact
    ? "max-h-[min(200px,35vh)] min-h-[72px] overflow-y-auto border border-cyan-900/40 bg-zinc-950/80 p-1.5 font-mono text-[10px] leading-snug text-zinc-200"
    : "max-h-[min(320px,50vh)] min-h-[120px] overflow-y-auto border border-cyan-900/40 bg-zinc-950/80 p-2 font-mono text-[11px] leading-5 text-zinc-200";

  if (messages.length === 0) {
    return <div className={emptyClass}>Waiting for game output…</div>;
  }

  return (
    <div className={listClass}>
      {messages.map((msg) => (
        <div
          key={msg.seq}
          className="mb-1 break-words"
          dangerouslySetInnerHTML={{ __html: msg.html }}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
