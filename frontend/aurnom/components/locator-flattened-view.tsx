"use client";

import { useMemo } from "react";

import { hopDistancesFromCurrent, outboundExitsByRoomKey } from "@/lib/locator-helpers";
import type { WorldGraphState } from "@/lib/ui-api";

export type LocatorFlattenedViewProps = {
  data: WorldGraphState;
  filter: string;
  adjacentKeys: Set<string> | null;
  reachableIds: Set<number> | null;
  travelBusy: boolean;
  onTravelTo: (roomKey: string) => void;
  onPrefetchRoom: (roomKey: string) => void;
};

export function LocatorFlattenedView({
  data,
  filter,
  adjacentKeys,
  reachableIds,
  travelBusy,
  onTravelTo,
  onPrefetchRoom,
}: LocatorFlattenedViewProps) {
  const q = filter.trim().toLowerCase();
  const hops = useMemo(
    () => hopDistancesFromCurrent(data.rooms, data.edges, data.currentRoomKey),
    [data.rooms, data.edges, data.currentRoomKey],
  );
  const outbound = useMemo(() => outboundExitsByRoomKey(data.edges), [data.edges]);

  const rows = useMemo(() => {
    const list = data.rooms
      .filter((r) => !q || r.key.toLowerCase().includes(q))
      .slice()
      .sort((a, b) => a.key.localeCompare(b.key));
    return list;
  }, [data.rooms, q]);

  return (
    <div className="rounded border border-cyan-900/40 bg-zinc-950">
      <p id="locator-flattened-desc" className="border-b border-cyan-900/30 px-2 py-2 text-[10px] text-zinc-500">
        Alphabetical directory with hop counts and exits. Use <span className="text-cyan-400">Travel</span> only
        for one-step destinations (same as &quot;Go&quot; on the graph).
      </p>
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
                    {exits.length === 0 ? (
                      <span className="text-zinc-600">—</span>
                    ) : (
                      <ul className="list-inside list-disc space-y-0.5">
                        {exits.map((ex) => (
                          <li key={`${ex.exitKey}→${ex.toKey}`}>
                            <span className="text-cyan-600/90">{ex.exitKey}</span>
                            <span className="text-zinc-600"> → </span>
                            {ex.toKey}
                          </li>
                        ))}
                      </ul>
                    )}
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
