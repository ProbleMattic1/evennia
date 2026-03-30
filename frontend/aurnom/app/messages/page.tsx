"use client";

import { useMemo } from "react";

import { useMsgStream } from "@/lib/use-msg-stream";

function disp(v: string | null) {
  if (v == null || v === "") return "—";
  return v;
}

export default function MessagesPage() {
  const { messages, clear } = useMsgStream();

  const newestFirst = useMemo(() => [...messages].reverse(), [messages]);

  return (
    <div className="dark min-h-svh overflow-y-auto border-l border-cyan-900/40 bg-zinc-950 p-2 font-mono text-xs text-foreground">
      <div className="mb-2 flex flex-wrap items-center gap-2 border-b border-cyan-900/40 pb-2">
        <h1 className="text-xs font-bold uppercase tracking-widest text-cyber-cyan">Messages</h1>
        <span className="text-xs text-ui-muted">{messages.length} in buffer</span>
        <button
          type="button"
          onClick={() => clear()}
          className="ml-auto rounded border border-cyan-800/60 px-2 py-0.5 text-xs text-cyber-cyan hover:bg-cyan-900/40"
        >
          Clear local view
        </button>
      </div>

      {newestFirst.length === 0 ? (
        <div className="rounded border border-cyan-900/40 bg-zinc-950/80 p-3 text-ui-muted">Waiting for game output…</div>
      ) : (
        <ul className="space-y-2">
          {newestFirst.map((m) => (
            <li
              key={m.seq}
              className="rounded border border-cyan-900/40 bg-zinc-950/80 p-2"
            >
              <div className="mb-1.5 grid gap-1 text-xs sm:grid-cols-2">
                <div className="flex min-w-0 gap-1">
                  <span className="shrink-0 text-ui-muted">seq</span>
                  <span className="font-mono text-foreground">{m.seq}</span>
                </div>
                <div className="flex min-w-0 gap-1">
                  <span className="shrink-0 text-ui-muted">ts</span>
                  <span className="min-w-0 break-all font-mono text-foreground">
                    {new Date(m.ts * 1000).toISOString()}
                  </span>
                </div>
                <div className="flex min-w-0 gap-1 sm:col-span-2">
                  <span className="shrink-0 text-ui-muted">eventType</span>
                  <span className="font-mono text-foreground">{disp(m.meta.eventType)}</span>
                </div>
                <div className="flex min-w-0 gap-1">
                  <span className="shrink-0 text-ui-muted">interactionKey</span>
                  <span className="min-w-0 break-words font-mono text-foreground">
                    {disp(m.meta.interactionKey)}
                  </span>
                </div>
                <div className="flex min-w-0 gap-1">
                  <span className="shrink-0 text-ui-muted">speakerKey</span>
                  <span className="min-w-0 break-words font-mono text-foreground">{disp(m.meta.speakerKey)}</span>
                </div>
                <div className="flex min-w-0 gap-1 sm:col-span-2">
                  <span className="shrink-0 text-ui-muted">destinationRoomKey</span>
                  <span className="min-w-0 break-words font-mono text-foreground">
                    {disp(m.meta.destinationRoomKey)}
                  </span>
                </div>
              </div>
              <div className="text-xs uppercase tracking-wide text-ui-muted">html</div>
              <div
                className="mt-0.5 break-words border border-zinc-800/80 bg-zinc-950 p-1.5 text-foreground leading-snug [&_a]:text-cyber-cyan"
                dangerouslySetInnerHTML={{ __html: m.html }}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
