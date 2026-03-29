"use client";

import { useMemo, useState } from "react";

import {
  hopDistancesFromCurrent,
  isIndustrialPadRoomKey,
  outboundExitDisplayPieces,
  outboundExitsByRoomKey,
  type OutboundExit,
  type OutboundExitDisplayPiece,
} from "@/lib/locator-helpers";
import type { WorldGraphState } from "@/lib/ui-api";

/** Wrap the whole exit list when there are many raw edges (even after pad clustering). */
const OUTER_COLLAPSE_MIN_EXITS = 8;

export type LocatorFlattenedViewProps = {
  data: WorldGraphState;
  filter: string;
  adjacentKeys: Set<string> | null;
  reachableIds: Set<number> | null;
  travelBusy: boolean;
  onTravelTo: (roomKey: string) => void;
  onPrefetchRoom: (roomKey: string) => void;
};

function exitPieceKey(piece: OutboundExitDisplayPiece, index: number): string {
  if (piece.kind === "single") {
    return `s-${piece.ex.exitKey}→${piece.ex.toKey}`;
  }
  return `c-${piece.cluster.label}-${index}`;
}

function SingleExitLine({ ex }: { ex: OutboundExit }) {
  return (
    <>
      <span className="text-cyan-600/90">{ex.exitKey}</span>
      <span className="text-zinc-600"> → </span>
      {ex.toKey}
    </>
  );
}

function OutboundExitsCell({ exits, roomId }: { exits: OutboundExit[]; roomId: number }) {
  if (exits.length === 0) {
    return <span className="text-zinc-600">—</span>;
  }

  const pieces = outboundExitDisplayPieces(exits);
  const summaryId = `locator-exits-${roomId}`;
  const hasCluster = pieces.some((p) => p.kind === "cluster");

  const list = (
    <ul className="list-inside list-disc space-y-0.5">
      {pieces.map((piece, i) =>
        piece.kind === "single" ? (
          <li key={exitPieceKey(piece, i)}>
            <SingleExitLine ex={piece.ex} />
          </li>
        ) : (
          <li key={exitPieceKey(piece, i)} className="list-none">
            <details className="ml-[-0.5rem]">
              <summary className="cursor-pointer select-none text-cyan-600/90 hover:text-cyan-400">
                {piece.cluster.label}{" "}
                <span className="text-zinc-500">({piece.cluster.count})</span>
              </summary>
              <ul className="mt-1 list-inside list-disc space-y-0.5 border-l border-zinc-800 pl-2 text-zinc-400">
                {piece.cluster.exits.map((ex) => (
                  <li key={`${ex.exitKey}→${ex.toKey}`}>
                    <SingleExitLine ex={ex} />
                  </li>
                ))}
              </ul>
            </details>
          </li>
        ),
      )}
    </ul>
  );

  const useOuterCollapse = exits.length >= OUTER_COLLAPSE_MIN_EXITS || hasCluster;
  if (!useOuterCollapse) {
    return list;
  }

  const summaryBits: string[] = [];
  if (hasCluster) summaryBits.push("pad routes grouped");
  if (exits.length >= OUTER_COLLAPSE_MIN_EXITS) summaryBits.push(`${exits.length} exits`);

  return (
    <details id={summaryId}>
      <summary className="cursor-pointer select-none text-zinc-400 hover:text-zinc-300">
        {summaryBits.join(" · ")} — <span className="text-cyan-600/80">expand</span>
      </summary>
      <div className="mt-1 border-t border-zinc-800/80 pt-1">{list}</div>
    </details>
  );
}

export function LocatorFlattenedView({
  data,
  filter,
  adjacentKeys,
  reachableIds,
  travelBusy,
  onTravelTo,
  onPrefetchRoom,
}: LocatorFlattenedViewProps) {
  const [showPadBays, setShowPadBays] = useState(false);
  const q = filter.trim().toLowerCase();
  const hops = useMemo(
    () => hopDistancesFromCurrent(data.rooms, data.edges, data.currentRoomKey),
    [data.rooms, data.edges, data.currentRoomKey],
  );
  const outbound = useMemo(() => outboundExitsByRoomKey(data.edges), [data.edges]);

  const industrialPadBayCount = useMemo(
    () => data.rooms.filter((r) => isIndustrialPadRoomKey(r.key)).length,
    [data.rooms],
  );

  const rows = useMemo(() => {
    const here = data.currentRoomKey;
    const list = data.rooms
      .filter((r) => {
        const textMatch = !q || r.key.toLowerCase().includes(q);
        if (!textMatch) return false;
        if (here && r.key === here) return true;
        if (!showPadBays && isIndustrialPadRoomKey(r.key) && !q) return false;
        return true;
      })
      .slice()
      .sort((a, b) => a.key.localeCompare(b.key));
    return list;
  }, [data.rooms, data.currentRoomKey, q, showPadBays]);

  return (
    <div className="rounded border border-cyan-900/40 bg-zinc-950">
      <p id="locator-flattened-desc" className="border-b border-cyan-900/30 px-2 py-2 text-[10px] text-zinc-500">
        Directory by location (hops + exits). Industrial <span className="text-amber-600/90">pad bays</span> are omitted
        from the table until you search or enable the checkbox — staging grids stay one row each. Staging exits stay
        collapsed until expanded. <span className="text-cyan-400">Travel</span> = one hop only (same as Graph &quot;Go&quot;).
      </p>
      {industrialPadBayCount > 0 ? (
        <div className="flex flex-wrap items-center gap-2 border-b border-cyan-900/20 px-2 py-1.5 font-mono text-[10px] text-zinc-500">
          <label className="flex cursor-pointer items-center gap-1.5 text-zinc-400 hover:text-zinc-300">
            <input
              type="checkbox"
              checked={showPadBays}
              onChange={(e) => setShowPadBays(e.target.checked)}
              className="accent-cyan-600"
            />
            Include industrial pad bays
          </label>
          <span className="text-zinc-600">
            (
            {showPadBays
              ? `${industrialPadBayCount} listed`
              : q
                ? "narrow search or check box for all bays"
                : `${industrialPadBayCount} bays omitted from table`}
            )
          </span>
        </div>
      ) : null}
      <div className="max-h-[min(60vh,640px)] min-h-[320px] overflow-auto">
        <table
          className="w-full border-collapse font-mono text-[10px] text-zinc-300"
          aria-describedby="locator-flattened-desc"
        >
          <thead className="sticky top-0 z-[1] bg-zinc-900/95 text-left text-zinc-500">
            <tr>
              <th scope="col" className="border-b border-cyan-900/40 px-2 py-1.5 font-normal">
                Location
              </th>
              <th scope="col" className="border-b border-cyan-900/40 px-2 py-1.5 font-normal">
                Hops
              </th>
              <th scope="col" className="border-b border-cyan-900/40 px-2 py-1.5 font-normal">
                Outbound exits
              </th>
              <th scope="col" className="border-b border-cyan-900/40 px-2 py-1.5 font-normal">
                Action
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const here = data.currentRoomKey === r.key;
              const canStep = adjacentKeys?.has(r.key) ?? false;
              const hop = hops.get(r.id);
              const reachable = reachableIds ? reachableIds.has(r.id) : true;
              const exits = outbound.get(r.key) ?? [];
              return (
                <tr
                  key={r.id}
                  className={here ? "bg-amber-950/40" : reachable ? "" : "opacity-50"}
                  aria-current={here ? "location" : undefined}
                >
                  <td className="border-b border-zinc-800/80 px-2 py-1.5 align-top">
                    <span className="font-semibold text-zinc-100">{r.key}</span>
                    <span className="ml-1 inline-flex flex-wrap gap-0.5">
                      {here ? (
                        <span className="rounded bg-amber-900/50 px-1 text-[9px] uppercase text-amber-200">
                          You
                        </span>
                      ) : null}
                      {r.hasMiningSite ? (
                        <span className="rounded bg-amber-950/80 px-1 text-[9px] text-amber-500/90">Mine</span>
                      ) : null}
                    </span>
                  </td>
                  <td className="border-b border-zinc-800/80 px-2 py-1.5 align-top text-zinc-500">
                    {hop !== undefined ? hop : "—"}
                  </td>
                  <td className="border-b border-zinc-800/80 px-2 py-1.5 align-top text-zinc-400">
                    <OutboundExitsCell exits={exits} roomId={r.id} />
                  </td>
                  <td className="border-b border-zinc-800/80 px-2 py-1.5 align-top">
                    {canStep && !here ? (
                      <button
                        type="button"
                        disabled={travelBusy}
                        className="rounded border border-cyan-700/60 bg-cyan-950/50 px-2 py-0.5 text-cyan-300 hover:bg-cyan-900/40 disabled:opacity-40"
                        onClick={() => onTravelTo(r.key)}
                        onMouseEnter={() => onPrefetchRoom(r.key)}
                      >
                        Travel
                      </button>
                    ) : here ? (
                      <span className="text-zinc-600">—</span>
                    ) : (
                      <span className="text-zinc-600" title="Not adjacent">
                        —
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
