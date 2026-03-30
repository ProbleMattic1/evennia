"use client";

import React, { useCallback, useMemo, type CSSProperties } from "react";
import { ResponsiveContainer, Treemap, type TreemapNode } from "recharts";

import { buildStationTreemapData } from "@/lib/locator-treemap-tree";
import type { WorldGraphState } from "@/lib/ui-api";

function districtHeatFill(maxPlayer: number, playerCount: number): string {
  const t = maxPlayer > 0 ? Math.min(1, Math.max(0, playerCount / maxPlayer)) : 0;
  const hue = 200 - t * 120;
  return `hsl(${hue}, 70%, 20%)`;
}

type TreemapCellCtx = {
  data: WorldGraphState;
  maxPlayerCount: number;
  adjacentKeys: Set<string> | null;
  reachableIds: Set<number> | null;
  travelBusy: boolean;
  onTravelTo: (roomKey: string) => void;
  onPrefetchRoom: (roomKey: string) => void;
};

type CellProps = TreemapNode &
  TreemapCellCtx & {
    roomKey?: string;
    roomId?: number;
    playerCount?: number;
    hasMiningSite?: boolean;
    parcelSummary?: boolean;
    parcelTier?: number;
    parcelZone?: string;
  };

function LocatorTreemapCell(props: CellProps) {
  const {
    x,
    y,
    width,
    height,
    name,
    depth,
    children,
    data,
    maxPlayerCount,
    adjacentKeys,
    reachableIds,
    travelBusy,
    onTravelTo,
    onPrefetchRoom,
    roomKey,
    roomId,
    playerCount = 0,
    hasMiningSite = false,
    parcelSummary = false,
    parcelTier,
    parcelZone,
  } = props;

  const isLeaf = !children || children.length === 0;

  if (depth === 0) {
    return <g />;
  }

  if (!isLeaf) {
    const showLabel = width > 48 && height > 18;
    return (
      <g>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          rx={3}
          ry={3}
          fill="rgba(9, 40, 52, 0.45)"
          stroke="rgba(6, 182, 212, 0.35)"
          strokeWidth={1}
        />
        {showLabel ? (
          <text
            x={x + 6}
            y={y + 13}
            fill="rgb(103, 232, 249)"
            fontSize={11}
            fontWeight={700}
            style={{ fontFamily: "ui-monospace, monospace" }}
          >
            {name}
          </text>
        ) : null}
      </g>
    );
  }

  const rk = roomKey ?? "";
  const rid = roomId ?? -1;
  const here = !parcelSummary && rk && data.currentRoomKey === rk;
  const canStep = !parcelSummary && rk ? (adjacentKeys?.has(rk) ?? false) : false;
  const reachable = parcelSummary ? true : reachableIds ? reachableIds.has(rid) : true;
  const fill = here
    ? "rgba(69, 26, 3, 0.75)"
    : parcelSummary
      ? "rgba(76, 29, 149, 0.32)"
      : districtHeatFill(maxPlayerCount, playerCount);
  const stroke = parcelSummary
    ? "rgba(167, 139, 250, 0.55)"
    : here
      ? "rgb(245, 158, 11)"
      : canStep
        ? "rgba(6, 182, 212, 0.55)"
        : "rgba(63, 63, 70, 0.9)";
  const strokeW = here ? 2 : 1;
  const tierNote =
    parcelSummary && (parcelTier != null || parcelZone)
      ? ` — ${parcelZone ?? "parcel"}${parcelTier != null ? ` · tier ${parcelTier}` : ""}`
      : "";
  const label = parcelSummary
    ? `${name}${tierNote} (anchored to promenade)`
    : `${rk || name}, ${playerCount} player${playerCount === 1 ? "" : "s"} here`;

  const onLeafClick = () => {
    if (parcelSummary) return;
    if (canStep && !here && rk) onTravelTo(rk);
  };

  const foStyle: CSSProperties = {
    width: "100%",
    height: "100%",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
    padding: "4px",
    boxSizing: "border-box",
    overflow: "hidden",
  };

  const showBody = width > 52 && height > 44;

  return (
    <g opacity={reachable ? 1 : 0.45}>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={2}
        ry={2}
        fill={fill}
        stroke={stroke}
        strokeWidth={strokeW}
        pointerEvents="all"
        data-recharts-item-index={props.tooltipIndex}
        aria-label={label}
        onClick={onLeafClick}
        onMouseEnter={() => !parcelSummary && rk && onPrefetchRoom(rk)}
        style={{ cursor: !parcelSummary && canStep && !here ? "pointer" : "default" }}
      />
      {width > 36 && height > 28 ? (
        <foreignObject x={x} y={y} width={width} height={height} pointerEvents="none">
          {React.createElement(
            "div",
            { xmlns: "http://www.w3.org/1999/xhtml", style: foStyle },
            <>
              <div className="min-w-0">
                <div
                  className="truncate font-mono text-ui-caption font-semibold leading-tight text-foreground"
                  title={rk || name}
                >
                  {name}
                </div>
                <div className="mt-0.5 flex flex-wrap gap-0.5">
                  {here ? (
                    <span className="rounded bg-amber-900/60 px-1 text-ui-micro uppercase text-amber-200">You</span>
                  ) : null}
                  {hasMiningSite ? (
                    <span className="rounded bg-amber-950/80 px-1 text-ui-micro text-amber-400">Mine</span>
                  ) : null}
                  {parcelSummary ? (
                    <span className="rounded bg-violet-950/80 px-1 text-ui-micro text-violet-300">Parcel</span>
                  ) : null}
                  {canStep && !here ? (
                    <span className="rounded bg-cyan-900/50 px-1 text-ui-micro text-cyber-cyan">Adj</span>
                  ) : null}
                  <span
                    className="rounded bg-zinc-900/90 px-1 text-ui-micro tabular-nums text-ui-muted"
                    title="Player characters in this room (excludes NPCs)"
                  >
                    {playerCount}
                  </span>
                </div>
              </div>
              {showBody ? (
                <div className="mt-auto shrink-0">
                  {parcelSummary ? (
                    <span className="text-ui-micro leading-tight text-violet-200/90">
                      Hub-anchored titled parcel{rk ? " · shell on map" : ""}
                    </span>
                  ) : canStep && !here ? (
                    <button
                      type="button"
                      disabled={travelBusy}
                      className="w-full rounded border border-cyan-700/60 bg-cyan-950/70 py-0.5 text-ui-overline text-cyber-cyan hover:bg-cyan-900/50 disabled:opacity-40"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (rk) onTravelTo(rk);
                      }}
                      onMouseEnter={() => rk && onPrefetchRoom(rk)}
                    >
                      Travel
                    </button>
                  ) : here ? (
                    <span className="text-ui-micro text-ui-muted">Current location</span>
                  ) : (
                    <span className="text-ui-micro text-ui-soft">Not adjacent</span>
                  )}
                </div>
              ) : null}
            </>,
          )}
        </foreignObject>
      ) : (
        <title>{label}</title>
      )}
    </g>
  );
}

export type LocatorGridViewProps = {
  data: WorldGraphState;
  filter: string;
  adjacentKeys: Set<string> | null;
  reachableIds: Set<number> | null;
  travelBusy: boolean;
  onTravelTo: (roomKey: string) => void;
  onPrefetchRoom: (roomKey: string) => void;
};

export function LocatorGridView({
  data,
  filter,
  adjacentKeys,
  reachableIds,
  travelBusy,
  onTravelTo,
  onPrefetchRoom,
}: LocatorGridViewProps) {
  const { treemapData, maxPlayerCount, empty } = useMemo(
    () => {
      const b = buildStationTreemapData(
        data.rooms,
        filter,
        data.venueCatalog ?? [],
        data.locatorParcels,
      );
      return { treemapData: b.data, maxPlayerCount: b.maxPlayerCount, empty: b.empty };
    },
    [data.rooms, data.venueCatalog, data.locatorParcels, filter],
  );

  const renderContent = useCallback(
    (nodeProps: TreemapNode) => (
      <LocatorTreemapCell
        {...nodeProps}
        data={data}
        maxPlayerCount={maxPlayerCount}
        adjacentKeys={adjacentKeys}
        reachableIds={reachableIds}
        travelBusy={travelBusy}
        onTravelTo={onTravelTo}
        onPrefetchRoom={onPrefetchRoom}
      />
    ),
    [
      data,
      maxPlayerCount,
      adjacentKeys,
      reachableIds,
      travelBusy,
      onTravelTo,
      onPrefetchRoom,
    ],
  );

  return (
    <div className="max-h-[min(72vh,720px)] min-h-[320px] rounded border border-cyan-900/40 bg-zinc-950 p-2">
      <p className="mb-2 text-xs text-ui-muted">
        Station <span className="text-ui-muted">treemap</span>: rectangle area ≈ relative scale (hub &amp; concourses
        vs industrial pads &amp; claims). Each <span className="text-cyber-cyan">venue</span> from the server gets its own
        block for promenade-adjacent rooms; industrial pads split by venue where needed (e.g. plex vs frontier).{" "}
        <span className="text-violet-300">Titled parcels</span> (per venue) anchor to the hub; color ≈ player density
        in parcel shells. <span className="text-cyber-cyan">Travel</span> when adjacent (room leaves only).
      </p>
      {empty ? (
        <div className="flex min-h-[280px] items-center justify-center text-xs text-ui-muted">
          No locations match this filter.
        </div>
      ) : (
        <div className="h-[min(64vh,640px)] min-h-[280px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <Treemap
              data={treemapData}
              dataKey="value"
              nameKey="name"
              stroke="rgba(24, 24, 27, 0.85)"
              content={renderContent}
              isAnimationActive={false}
              isUpdateAnimationActive={false}
              aspectRatio={4 / 3}
            />
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
