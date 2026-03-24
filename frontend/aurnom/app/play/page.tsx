"use client";

import { Suspense, useCallback } from "react";
import { useSearchParams } from "next/navigation";

import { ActionGrid } from "@/components/action-grid";
import { CommodityTickerStrip, CommodityTickerTable } from "@/components/commodity-ticker";
import { ExitGrid } from "@/components/exit-grid";
import { MineDetailsPanel } from "@/components/mine-details-panel";
import { StoryPanel } from "@/components/story-panel";
import { getPlayState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

const MINING_OUTFITTERS_ROOM = "Aurnom Mining Outfitters";

function PlayPageInner() {
  const searchParams = useSearchParams();
  const room = searchParams.get("room") ?? undefined;
  const loader = useCallback(() => getPlayState(room), [room]);
  const { data, error, loading } = useUiResource(loader);

  if (loading) {
    return (
      <main className="main-content">
        <p className="text-sm text-zinc-500 dark:text-cyan-500/80">Loading play state…</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="main-content">
        <p className="text-sm text-red-600 dark:text-red-400">Failed to load play state: {error ?? "Unknown error"}</p>
      </main>
    );
  }

  return (
    <main className="main-content">
      <header className="border-b border-zinc-200 py-3 dark:border-cyan-900/50">
        <div className="px-2">
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">Play</h1>
          <p className="mt-0.5 text-[12px] text-zinc-500 dark:text-cyan-500/80">Current location: {data.roomName}</p>
        </div>
      </header>

      {data.roomName === MINING_OUTFITTERS_ROOM && <CommodityTickerStrip />}

      <div className="grid gap-2 px-2 py-2 lg:grid-cols-[1.5fr_1fr]">
        <div className="flex flex-col gap-2">
          <StoryPanel title="Story Output" lines={data.storyLines} />
          {data.site && <MineDetailsPanel site={data.site} />}
        </div>
        <div className="flex flex-col gap-2">
          <ExitGrid exits={data.exits} />
          <ActionGrid actions={data.actions} />
        </div>
      </div>

      {data.roomName === MINING_OUTFITTERS_ROOM && <CommodityTickerTable />}
    </main>
  );
}

export default function PlayPage() {
  return (
    <Suspense
      fallback={
        <main className="main-content">
          <p className="text-sm text-zinc-500 dark:text-cyan-500/80">Loading play state…</p>
        </main>
      }
    >
      <PlayPageInner />
    </Suspense>
  );
}
