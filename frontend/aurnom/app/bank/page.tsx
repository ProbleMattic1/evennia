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
      <main className="mx-auto flex w-full max-w-6xl flex-1 px-6 py-10">
        <p className="text-zinc-600">Loading bank state...</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 px-6 py-10">
        <p className="text-red-600">Failed to load bank state: {error ?? "Unknown error"}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-zinc-950">{data.bankName}</h1>
          <p className="mt-2 text-zinc-600">{data.roomName}</p>
        </div>
        <Link
          href="/play?room=Alpha%20Prime%20Central%20Reserve"
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white"
        >
          Back to Play
        </Link>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <StoryPanel title="Bank Output" lines={data.storyLines} />
        <div className="flex flex-col gap-6">
          <section className="rounded-xl border border-zinc-200 bg-white p-4">
            <h2 className="text-lg font-semibold text-zinc-900">Treasury</h2>
            <p className="mt-3 text-3xl font-bold text-zinc-950">
              {data.treasuryBalance.toLocaleString()} cr
            </p>
          </section>
          <ExitGrid exits={data.exits} />
        </div>
      </div>
    </main>
  );
}
