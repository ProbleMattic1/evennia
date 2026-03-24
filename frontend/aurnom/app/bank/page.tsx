"use client";

import { useCallback } from "react";
import Link from "next/link";

import { ExitGrid } from "@/components/exit-grid";
import { StoryPanel } from "@/components/story-panel";
import { getBankState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

export default function BankPage() {
  const loader = useCallback(() => getBankState(), []);
  const { data, error, loading } = useUiResource(loader);

  if (loading) {
    return (
      <main className="main-content">
        <p className="text-sm text-zinc-500 dark:text-cyan-500/80">Loading bank state…</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="main-content">
        <p className="text-sm text-red-600 dark:text-red-400">Failed to load bank state: {error ?? "Unknown error"}</p>
      </main>
    );
  }

  return (
    <main className="main-content">
      <header className="flex items-center justify-between border-b border-zinc-200 py-3 dark:border-cyan-900/50">
        <div className="px-2">
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">{data.bankName}</h1>
          <p className="mt-0.5 text-[12px] text-zinc-500 dark:text-cyan-500/80">{data.roomName}</p>
        </div>
        <Link
          href="/play?room=Alpha%20Prime%20Central%20Reserve"
          className="rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-800 hover:bg-zinc-100 dark:border-cyan-700/50 dark:text-cyan-400 dark:hover:bg-cyan-950/40 dark:hover:text-cyan-300"
        >
          Back to Play
        </Link>
      </header>

      <div className="grid gap-2 px-2 py-2 lg:grid-cols-[1.5fr_1fr]">
        <StoryPanel title="Bank Output" lines={data.storyLines} />
        <div className="flex flex-col gap-2">
          <section className="border-b border-zinc-100 px-2 py-2 dark:border-cyan-900/30">
            <h2 className="section-label">Treasury</h2>
            <p className="mt-1 font-mono text-sm font-semibold tabular-nums text-zinc-800 dark:text-zinc-200">
              {data.treasuryBalance.toLocaleString()} cr
            </p>
          </section>
          <ExitGrid exits={data.exits} />
        </div>
      </div>
    </main>
  );
}
