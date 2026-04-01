"use client";

import { Suspense, useCallback, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";

import { useControlSurface } from "@/components/control-surface-provider";
import { CsButtonLink, CsColumns, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { CommodityTickerStrip, CommodityTickerTable } from "@/components/commodity-ticker";
import { ExitGrid } from "@/components/exit-grid";
import { LocationBanner } from "@/components/location-banner";
import {
  MineDetailsPanel,
  MinePlayRightColumn,
  PlayMissionsPanel,
  PlayQuestsPanel,
} from "@/components/mine-details-panel";
import { StoryPanel } from "@/components/story-panel";
import { EMPTY_ROOM_AMBIENT, getPlayState } from "@/lib/ui-api";
import { UI_REFRESH_MS } from "@/lib/ui-refresh-policy";
import { useMsgStream } from "@/lib/use-msg-stream";
import { useReloadAfterIso } from "@/lib/use-reload-after-iso";
import { useUiResource } from "@/lib/use-ui-resource";

const MINING_OUTFITTERS_ROOM = "Aurnom Mining Outfitters";

function PlayPageInner() {
  const searchParams = useSearchParams();
  const room = searchParams.get("room") ?? undefined;
  const loader = useCallback(() => getPlayState(room), [room]);
  const { data, error, loading, reload } = useUiResource(loader);
  const { puppetLocationSeq } = useControlSurface();
  const playBoot = useRef(false);
  useEffect(() => {
    if (!playBoot.current) {
      playBoot.current = true;
      return;
    }
    reload();
  }, [puppetLocationSeq, reload]);
  const { messages: streamMessages } = useMsgStream();

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

  const ambient = data.ambient ?? EMPTY_ROOM_AMBIENT;
  const useCommodityBoard =
    data.site &&
    (ambient.layoutHints?.rightColumn === "commodity_board" || data.roomName === MINING_OUTFITTERS_ROOM);

  const mineRight =
    useCommodityBoard ? (
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
        <CsPanel title="Main quests">
          <PlayQuestsPanel onPlayReload={reload} />
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
      <LocationBanner
        ambient={ambient}
        roomName={data.roomName}
        variant="full"
        messages={streamMessages}
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
                <MineDetailsPanel site={data.site} />
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
          <p className="text-sm text-ui-accent-readable">Loading play state…</p>
        </CsPage>
      }
    >
      <PlayPageInner />
    </Suspense>
  );
}
