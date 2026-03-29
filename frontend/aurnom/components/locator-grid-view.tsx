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
  const here = rk && data.currentRoomKey === rk;
  const canStep = rk ? (adjacentKeys?.has(rk) ?? false) : false;
  const reachable = reachableIds ? reachableIds.has(rid) : true;
  const fill = here ? "rgba(69, 26, 3, 0.75)" : districtHeatFill(maxPlayerCount, playerCount);
  const stroke = here ? "rgb(245, 158, 11)" : canStep ? "rgba(6, 182, 212, 0.55)" : "rgba(63, 63, 70, 0.9)";
  const strokeW = here ? 2 : 1;
  const label = `${rk || name}, ${playerCount} player${playerCount === 1 ? "" : "s"} here`;

  const onLeafClick = () => {
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
        onMouseEnter={() => rk && onPrefetchRoom(rk)}
        style={{ cursor: canStep && !here ? "pointer" : "default" }}
      />
      {width > 36 && height > 28 ? (
        <foreignObject x={x} y={y} width={width} height={height} pointerEvents="none">
          {React.createElement(
            "div",
            { xmlns: "http://www.w3.org/1999/xhtml", style: foStyle },
            <>
              <div className="min-w-0">
                <div
                  className="truncate font-mono text-[9px] font-semibold leading-tight text-zinc-100"
                  title={rk || name}
                >
                  {name}
                </div>
                <div className="mt-0.5 flex flex-wrap gap-0.5">
                  {here ? (
                    <span className="rounded bg-amber-900/60 px-1 text-[7px] uppercase text-amber-200">You</span>
                  ) : null}
                  {hasMiningSite ? (
                    <span className="rounded bg-amber-950/80 px-1 text-[7px] text-amber-500/90">Mine</span>
                  ) : null}
                  {canStep && !here ? (
                    <span className="rounded bg-cyan-900/50 px-1 text-[7px] text-cyan-300">Adj</span>
                  ) : null}
                  <span
                    className="rounded bg-zinc-900/90 px-1 text-[7px] tabular-nums text-zinc-400"
                    title="Player characters in this room (excludes NPCs)"
                  >
                    {playerCount}
                  </span>
                </div>
              </div>
              {showBody ? (
                <div className="mt-auto shrink-0">
                  {canStep && !here ? (
                    <button
                      type="button"
                      disabled={travelBusy}
                      className="w-full rounded border border-cyan-700/60 bg-cyan-950/70 py-0.5 text-[8px] text-cyan-200 hover:bg-cyan-900/50 disabled:opacity-40"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (rk) onTravelTo(rk);
                      }}
                      onMouseEnter={() => rk && onPrefetchRoom(rk)}
                    >
                      Travel
                    </button>
                  ) : here ? (
                    <span className="text-[7px] text-zinc-500">Current location</span>
                  ) : (
                    <span className="text-[7px] text-zinc-600">Not adjacent</span>
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
      const b = buildStationTreemapData(data.rooms, filter);
      return { treemapData: b.data, maxPlayerCount: b.maxPlayerCount, empty: b.empty };
    },
    [data.rooms, filter],
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
      <p className="mb-2 text-[10px] text-zinc-500">
        Station <span className="text-zinc-400">treemap</span>: rectangle area ≈ relative scale (megaplex hub &amp;
        concourses vs industrial pads &amp; claims).{" "}
        <span className="text-cyan-400">NanoMegaPlex</span> nests promenade, retail, services, realty, meridian, and
        agency. Color ≈ player density in this view. <span className="text-cyan-400">Travel</span> when adjacent.
      </p>
      {empty ? (
        <div className="flex min-h-[280px] items-center justify-center text-[11px] text-zinc-500">
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
