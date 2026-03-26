"use client";

import { Suspense, useCallback, useEffect } from "react";
import { useSearchParams } from "next/navigation";

import { ActionGrid } from "@/components/action-grid";
import { CsButtonLink, CsColumns, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { CommodityTickerStrip, CommodityTickerTable } from "@/components/commodity-ticker";
import { MineDetailsPanel } from "@/components/mine-details-panel";
import { StoryPanel } from "@/components/story-panel";
import { getPlayState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

const MINING_OUTFITTERS_ROOM = "Aurnom Mining Outfitters";

function PlayPageInner() {
  const searchParams = useSearchParams();
  const room = searchParams.get("room") ?? undefined;
  const loader = useCallback(() => getPlayState(room), [room]);
  const { data, error, loading, reload } = useUiResource(loader);

  useEffect(() => {
    const iso = data?.site?.nextCycleAt;
    if (!iso) return;
    if (new Date(iso).getTime() > Date.now()) return;
    const id = setInterval(() => reload(), 15000);
    return () => clearInterval(id);
  }, [data?.site?.nextCycleAt, reload]);

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
    <CsPage>
      <CsHeader
        title="Play"
        subtitle={`Current location: ${data.roomName}`}
        actions={<CsButtonLink href="/">Dashboard</CsButtonLink>}
      />
      <CsColumns
        left={
          <>
            <CsPanel title="Actions">
              <ActionGrid actions={data.actions} />
            </CsPanel>
            <CsPanel title="Story Output">
              <StoryPanel title="Story Output" lines={data.storyLines} />
            </CsPanel>
            {data.site ? (
              <CsPanel title="Mine Site">
                <MineDetailsPanel site={data.site} onCycleCountdownExpired={reload} />
              </CsPanel>
            ) : null}
          </>
        }
        right={
          data.roomName === MINING_OUTFITTERS_ROOM ? (
            <>
              <CsPanel title="Market Snapshot">
                <CommodityTickerStrip />
              </CsPanel>
              <CsPanel title="Commodity Board">
                <CommodityTickerTable />
              </CsPanel>
            </>
          ) : undefined
        }
      />
    </CsPage>
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
