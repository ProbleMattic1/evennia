"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { ExitGrid } from "@/components/exit-grid";
import { StoryPanel } from "@/components/story-panel";
import {
  buyShip,
  getShipyardState,
  inspectShip,
  type ShipyardState,
  type StoryLine,
} from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

function appendSystemLine(lines: StoryLine[], text: string): StoryLine[] {
  return [...lines, { id: `sys-${Date.now()}`, text, kind: "system" }];
}

export default function ShipyardPage() {
  const loader = useCallback(() => getShipyardState(), []);
  const { data, error, loading } = useUiResource(loader);

  const [state, setState] = useState<ShipyardState | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<"inspect" | "buy" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setState(data);
    }
  }, [data]);

  const view = useMemo(() => state ?? data ?? null, [state, data]);

  async function onInspect(shipId: string, shipName: string) {
    try {
      setActionError(null);
      setBusyKey(shipId);
      setBusyAction("inspect");

      const res = await inspectShip({ shipId, name: shipName });
      if (res.state) {
        setState(res.state);
      }
      if (res.message) {
        setState((prev) =>
          prev ? { ...prev, storyLines: appendSystemLine(prev.storyLines, res.message) } : prev
        );
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Inspect failed");
    } finally {
      setBusyKey(null);
      setBusyAction(null);
    }
  }

  async function onBuy(shipId: string, shipName: string) {
    try {
      setActionError(null);
      setBusyKey(shipId);
      setBusyAction("buy");

      const res = await buyShip({ shipId, name: shipName });
      if (res.state) {
        setState(res.state);
      }
      if (res.message) {
        setState((prev) =>
          prev ? { ...prev, storyLines: appendSystemLine(prev.storyLines, res.message) } : prev
        );
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Purchase failed");
    } finally {
      setBusyKey(null);
      setBusyAction(null);
    }
  }

  if (loading) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 px-6 py-10">
        <p className="text-zinc-600">Loading shipyard state...</p>
      </main>
    );
  }

  if (error || !view) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 px-6 py-10">
        <p className="text-red-600">Failed to load shipyard state: {error ?? "Unknown error"}</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-zinc-950">{view.shopName}</h1>
          <p className="mt-2 text-zinc-600">{view.roomName}</p>
        </div>
        <Link
          href="/play?room=Meridian%20Civil%20Shipyard"
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white"
        >
          Back to Play
        </Link>
      </header>

      {actionError ? (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {actionError}
        </p>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <StoryPanel title="Shipyard Output" lines={view.storyLines} />

        <section className="rounded-xl border border-zinc-200 bg-white p-4">
          <h2 className="mb-3 text-lg font-semibold text-zinc-900">Ships for Sale</h2>
          <div className="space-y-4">
            {view.ships.map((ship) => {
              const rowBusy = busyKey === ship.id;
              return (
                <article key={ship.id} className="rounded-lg border border-zinc-200 p-4">
                  <h3 className="text-base font-semibold text-zinc-950">{ship.key}</h3>
                  <p className="mt-2 text-sm text-zinc-600">{ship.description}</p>
                  <p className="mt-3 text-sm text-zinc-800">{ship.summary}</p>
                  <p className="mt-3 text-sm font-medium text-zinc-950">
                    Price: {ship.price?.toLocaleString() ?? "N/A"} cr
                  </p>
                  <div className="mt-4 flex gap-2">
                    <button
                      type="button"
                      className="rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-800 disabled:text-zinc-500"
                      disabled={rowBusy}
                      onClick={() => onInspect(ship.id, ship.key)}
                    >
                      {rowBusy && busyAction === "inspect" ? "Inspecting..." : "Inspect"}
                    </button>
                    <button
                      type="button"
                      className="rounded-lg bg-zinc-900 px-3 py-2 text-sm text-white disabled:opacity-60"
                      disabled={rowBusy}
                      onClick={() => onBuy(ship.id, ship.key)}
                    >
                      {rowBusy && busyAction === "buy" ? "Buying..." : "Buy"}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>

      <ExitGrid exits={view.exits} />
    </main>
  );
}
