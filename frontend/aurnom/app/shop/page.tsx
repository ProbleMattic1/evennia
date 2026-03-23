"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { ExitGrid } from "@/components/exit-grid";
import { StoryPanel } from "@/components/story-panel";
import { buyItem, getShopState, inspectItem } from "@/lib/ui-api";
import type { ShopState } from "@/lib/ui-api";
import type { StoryLine } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

function appendSystemLine(lines: StoryLine[], text: string): StoryLine[] {
  return [...lines, { id: `sys-${Date.now()}`, text, kind: "system" }];
}

export default function ShopPage() {
  const searchParams = useSearchParams();
  const room = searchParams.get("room") ?? "";

  const loader = useCallback(() => getShopState(room), [room]);

  const { data, error, loading } = useUiResource(loader);

  const [state, setState] = useState<ShopState | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<"inspect" | "buy" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setState(data);
    }
  }, [data]);

  const view = useMemo(() => state ?? data ?? null, [state, data]);

  async function onInspect(itemId: string, itemName: string) {
    try {
      setActionError(null);
      setBusyKey(itemId);
      setBusyAction("inspect");

      const res = await inspectItem({ room, itemId, name: itemName });
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

  async function onBuy(itemId: string, itemName: string) {
    try {
      setActionError(null);
      setBusyKey(itemId);
      setBusyAction("buy");

      const res = await buyItem({ room, itemId, name: itemName });
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
        <p className="text-zinc-600">Loading shop state...</p>
      </main>
    );
  }

  if (error || !view) {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 px-6 py-10">
        <p className="text-red-600">Failed to load shop state: {error ?? "Unknown error"}</p>
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
          href={`/play?room=${encodeURIComponent(view.roomName)}`}
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
        <StoryPanel title="Shop Output" lines={view.storyLines} />

        <section className="rounded-xl border border-zinc-200 bg-white p-4">
          <h2 className="mb-3 text-lg font-semibold text-zinc-900">Items for Sale</h2>
          <div className="space-y-4">
            {view.items.map((item) => {
              const rowBusy = busyKey === item.id;
              return (
                <article key={item.id} className="rounded-lg border border-zinc-200 p-4">
                  <h3 className="text-base font-semibold text-zinc-950">{item.key}</h3>
                  <p className="mt-2 text-sm text-zinc-600">{item.description}</p>
                  <p className="mt-3 text-sm text-zinc-800">{item.summary}</p>
                  <p className="mt-3 text-sm font-medium text-zinc-950">
                    Price: {item.price?.toLocaleString() ?? "N/A"} cr
                  </p>
                  <div className="mt-4 flex gap-2">
                    <button
                      type="button"
                      className="rounded-lg border border-zinc-300 px-3 py-2 text-sm text-zinc-800 disabled:text-zinc-500"
                      disabled={rowBusy}
                      onClick={() => onInspect(item.id, item.key)}
                    >
                      {rowBusy && busyAction === "inspect" ? "Inspecting..." : "Inspect"}
                    </button>
                    <button
                      type="button"
                      className="rounded-lg bg-zinc-900 px-3 py-2 text-sm text-white disabled:opacity-60"
                      disabled={rowBusy}
                      onClick={() => onBuy(item.id, item.key)}
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
