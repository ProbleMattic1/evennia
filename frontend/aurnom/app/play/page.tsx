"use client";

import { Suspense, useCallback, useEffect } from "react";
import { useSearchParams } from "next/navigation";

import { CsButtonLink, CsColumns, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { CommodityTickerStrip, CommodityTickerTable } from "@/components/commodity-ticker";
import { ExitGrid } from "@/components/exit-grid";
import { MineDetailsPanel, MinePlayRightColumn, PlayMissionsPanel } from "@/components/mine-details-panel";
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
      <CsPage>
        <p className="text-sm text-zinc-500 dark:text-cyan-500/80">Loading play state…</p>
      </CsPage>
    );
  }

  if (error || !data) {
    return (
      <CsPage>
        <p className="text-sm text-red-600 dark:text-red-400">Failed to load play state: {error ?? "Unknown error"}</p>
      </CsPage>
    );
  }

  const mineRight =
    data.site && data.roomName === MINING_OUTFITTERS_ROOM ? (
      <>
        <CsPanel title="Market Snapshot">
          <CommodityTickerStrip />
        </CsPanel>
        <CsPanel title="Commodity Board">
          <CommodityTickerTable />
        </CsPanel>
      </>
    ) : data.site ? (
      <>
        <CsPanel title="Missions">
          <PlayMissionsPanel onPlayReload={reload} />
        </CsPanel>
        <CsPanel title="Mine detail">
          <MinePlayRightColumn site={data.site} playActions={data.actions} onPlayReload={reload} />
        </CsPanel>
      </>
    ) : undefined;

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
            <CsPanel title="Story Output">
              <StoryPanel lines={data.storyLines} compact />
            </CsPanel>
            <CsPanel title="Destinations">
              <ExitGrid exits={data.exits} />
            </CsPanel>
            {data.site ? (
              <CsPanel title="Mine Site">
                <MineDetailsPanel site={data.site} onCycleCountdownExpired={reload} />
              </CsPanel>
            ) : null}
          </>
        }
        right={mineRight}
      />
    </CsPage>
  );
}

export default function PlayPage() {
  return (
    <Suspense
      fallback={
        <CsPage>
          <p className="text-sm text-zinc-500 dark:text-cyan-500/80">Loading play state…</p>
        </CsPage>
      }
    >
      <PlayPageInner />
    </Suspense>
  );
}
