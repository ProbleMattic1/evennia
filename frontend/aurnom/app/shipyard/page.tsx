"use client";

import { useCallback } from "react";
import Link from "next/link";

import { ExitGrid } from "@/components/exit-grid";
import { StoryPanel } from "@/components/story-panel";
import { getShipyardState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

export default function ShipyardPage() {
  const loader = useCallback(() => getShipyardState(), []);
  const { data, error, loading } = useUiResource(loader);

  if (loading) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 px-6 py-10">
        <p className="text-zinc-600">Loading shipyard state...</p>
      </main>
    );
  }

  if (error || !data) {
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
          <h1 className="text-3xl font-bold text-zinc-950">{data.shopName}</h1>
          <p className="mt-2 text-zinc-600">{data.roomName}</p>
        </div>
        <Link
          href="/play?room=Meridian%20Civil%20Shipyard"
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white"
        >
          Back to Play
        </Link>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <StoryPanel title="Shipyard Output" lines={data.storyLines} />

        <section className="rounded-xl border border-zinc-200 bg-white p-4">
          <h2 className="mb-3 text-lg font-semibold text-zinc-900">Ships for Sale</h2>
          <div className="space-y-4">
            {data.ships.map((ship) => (
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
                    className="rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-500"
                    disabled
                  >
                    Inspect (next step)
                  </button>
                  <button
                    type="button"
                    className="rounded-lg bg-zinc-900 px-3 py-2 text-sm text-zinc-500 opacity-60"
                    disabled
                  >
                    Buy (next step)
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>

      <ExitGrid exits={data.exits} />
    </main>
  );
}
