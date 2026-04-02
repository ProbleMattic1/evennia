"use client";

import { Suspense, useCallback, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";

import { useControlSurface } from "@/components/control-surface-provider";
import { CsButtonLink, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { CommodityTickerTable } from "@/components/commodity-ticker";
import { MineDetailsPanel, MinePlayRightColumn } from "@/components/mine-details-panel";
import { VenueBillboardStoryFrame } from "@/components/venue-billboard-story-frame";
import { EMPTY_ROOM_AMBIENT, getPlayState } from "@/lib/ui-api";
import { UI_REFRESH_MS } from "@/lib/ui-refresh-policy";
import { useReloadAfterIso } from "@/lib/use-reload-after-iso";
import { useUiResource } from "@/lib/use-ui-resource";

const MINING_OUTFITTERS_ROOM = "Aurnom Mining Outfitters";

function PlayPageInner() {
  const searchParams = useSearchParams();
  const room = searchParams.get("room") ?? undefined;
  const loader = useCallback(() => getPlayState(room), [room]);
  const { data, error, loading, reload } = useUiResource(loader);
  const {
    data: csData,
    loading: csLoading,
    error: csError,
    puppetLocationSeq,
  } = useControlSurface();
  const playBoot = useRef(false);
  useEffect(() => {
    if (!playBoot.current) {
      playBoot.current = true;
      return;
    }
    reload();
  }, [puppetLocationSeq, reload]);

  const iso = data?.miningNextCycleAt ?? data?.site?.nextCycleAt ?? null;
  useReloadAfterIso(iso, reload, UI_REFRESH_MS.postDeadlinePoll);

  if (loading) {
    return (
      <CsPage>
        <p className="text-sm text-ui-accent-readable">Loading play state…</p>
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

  if (csLoading && !csData) {
    return (
      <CsPage>
        <p className="text-sm text-ui-accent-readable">Loading control surface…</p>
      </CsPage>
    );
  }

  if (!csData) {
    return (
      <CsPage>
        <p className="text-sm text-red-600 dark:text-red-400">
          Failed to load control surface{csError ? `: ${csError}` : "."}
        </p>
      </CsPage>
    );
  }

  const ambient = data.ambient ?? EMPTY_ROOM_AMBIENT;
  const useCommodityBoard =
    data.site &&
    (ambient.layoutHints?.rightColumn === "commodity_board" || data.roomName === MINING_OUTFITTERS_ROOM);

  const stackTail = useCommodityBoard ? (
    <CsPanel title="Commodity Board">
      <CommodityTickerTable />
    </CsPanel>
  ) : data.site ? (
    <CsPanel title="Mine detail">
      <MinePlayRightColumn site={data.site} playActions={data.actions} onPlayReload={reload} />
    </CsPanel>
  ) : null;

  return (
    <CsPage>
      <CsHeader
        title="Play"
        subtitle={`Current location: ${data.roomName}`}
        actions={<CsButtonLink href="/">Dashboard</CsButtonLink>}
      />
      <VenueBillboardStoryFrame
        panelTitle="Location & story"
        roomName={data.roomName}
        ambient={ambient}
        storyLines={data.storyLines}
      />
      <div className="min-h-0 min-w-0 overflow-y-auto p-1.5 md:min-h-0">
        {data.site ? (
          <CsPanel title="Mine Site">
            <MineDetailsPanel site={data.site} />
          </CsPanel>
        ) : null}
        {stackTail}
      </div>
    </CsPage>
  );
}

export default function PlayPage() {
  return (
    <Suspense
      fallback={
        <CsPage>
          <p className="text-sm text-ui-accent-readable">Loading play state…</p>
        </CsPage>
      }
    >
      <PlayPageInner />
    </Suspense>
  );
}
