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
    <div className="dark min-h-svh overflow-y-auto border-l border-cyan-900/40 bg-zinc-950 p-2 font-mono text-[11px] text-zinc-300">
      <div className="mb-2 flex flex-wrap items-center gap-2 border-b border-cyan-900/40 pb-2">
        <h1 className="text-[12px] font-bold uppercase tracking-widest text-cyan-300">Messages</h1>
        <span className="text-[10px] text-ui-muted">{messages.length} in buffer</span>
        <button
          type="button"
          onClick={() => clear()}
          className="ml-auto rounded border border-cyan-800/60 px-2 py-0.5 text-[10px] text-cyan-400 hover:bg-cyan-900/40"
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
              <div className="mb-1.5 grid gap-1 text-[10px] sm:grid-cols-2">
                <div className="flex min-w-0 gap-1">
                  <span className="shrink-0 text-ui-muted">seq</span>
                  <span className="font-mono text-zinc-200">{m.seq}</span>
                </div>
                <div className="flex min-w-0 gap-1">
                  <span className="shrink-0 text-ui-muted">ts</span>
                  <span className="min-w-0 break-all font-mono text-zinc-200">
                    {new Date(m.ts * 1000).toISOString()}
                  </span>
                </div>
                <div className="flex min-w-0 gap-1 sm:col-span-2">
                  <span className="shrink-0 text-ui-muted">eventType</span>
                  <span className="font-mono text-zinc-200">{disp(m.meta.eventType)}</span>
                </div>
                <div className="flex min-w-0 gap-1">
                  <span className="shrink-0 text-ui-muted">interactionKey</span>
                  <span className="min-w-0 break-words font-mono text-zinc-200">
                    {disp(m.meta.interactionKey)}
                  </span>
                </div>
                <div className="flex min-w-0 gap-1">
                  <span className="shrink-0 text-ui-muted">speakerKey</span>
                  <span className="min-w-0 break-words font-mono text-zinc-200">{disp(m.meta.speakerKey)}</span>
                </div>
                <div className="flex min-w-0 gap-1 sm:col-span-2">
                  <span className="shrink-0 text-ui-muted">destinationRoomKey</span>
                  <span className="min-w-0 break-words font-mono text-zinc-200">
                    {disp(m.meta.destinationRoomKey)}
                  </span>
                </div>
              </div>
              <div className="text-[10px] uppercase tracking-wide text-ui-muted">html</div>
              <div
                className="mt-0.5 break-words border border-zinc-800/80 bg-zinc-950 p-1.5 text-zinc-200 leading-snug [&_a]:text-cyan-400"
                dangerouslySetInnerHTML={{ __html: m.html }}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
