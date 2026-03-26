"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { CsButtonLink, CsColumns, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { ExitGrid } from "@/components/exit-grid";
import { StoryPanel } from "@/components/story-panel";
import { buyItem, getShopState, inspectItem } from "@/lib/ui-api";
import type { ShopState } from "@/lib/ui-api";
import type { StoryLine } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

function appendSystemLine(lines: StoryLine[], text: string): StoryLine[] {
  return [...lines, { id: `sys-${Date.now()}`, text, kind: "system" }];
}

function ShopPageInner() {
  const searchParams = useSearchParams();
  const room = searchParams.get("room") ?? "";

  const loader = useCallback(() => getShopState(room), [room]);

  const { data, error, loading } = useUiResource(loader);

  const [state, setState] = useState<ShopState | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<"inspect" | "buy" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set());

  function toggleExpanded(id: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  useEffect(() => {
    if (data) {
      setState(data);
    }
  }, [data]);

  const view = useMemo(() => state ?? data ?? null, [state, data]);

  const isShips = view?.catalogMode === "ships";
  const catalog = isShips ? view?.ships ?? [] : view?.items ?? [];

  async function onInspect(id: string, name: string) {
    try {
      setActionError(null);
      setBusyKey(id);
      setBusyAction("inspect");

      const res = await inspectItem({
        room,
        itemId: id,
        shipId: id,
        name,
      });
      if (res.state) {
        setState(res.state);
      }
      if (res.message) {
        setState((prev) =>
          prev ? { ...prev, storyLines: appendSystemLine(prev.storyLines, res.message ?? "") } : prev
        );
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Inspect failed");
    } finally {
      setBusyKey(null);
      setBusyAction(null);
    }
  }

  async function onBuy(id: string, name: string) {
    try {
      setActionError(null);
      setBusyKey(id);
      setBusyAction("buy");

      const res = await buyItem({
        room,
        itemId: id,
        shipId: id,
        name,
      });
      if (res.state) {
        setState(res.state);
      }
      if (res.message) {
        setState((prev) =>
          prev ? { ...prev, storyLines: appendSystemLine(prev.storyLines, res.message ?? "") } : prev
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
      <main className="main-content">
        <p className="text-sm text-zinc-500 dark:text-cyan-500/80">Loading shop state…</p>
      </main>
    );
  }

  if (error || !view) {
    return (
      <main className="main-content">
        <p className="text-sm text-red-600 dark:text-red-400">Failed to load shop state: {error ?? "Unknown error"}</p>
      </main>
    );
  }

  return (
    <CsPage>
      <CsHeader
        title={view.shopName}
        subtitle={view.roomName}
        actions={<CsButtonLink href={`/play?room=${encodeURIComponent(view.roomName)}`}>Back to Play</CsButtonLink>}
      />

      {actionError ? (
        <p className="mx-1.5 mt-1 rounded border border-red-800/40 bg-red-950/30 px-1.5 py-1 text-[10px] text-red-300">
          {actionError}
        </p>
      ) : null}

      <CsColumns
        left={
          <>
            <CsPanel title="Exits">
              <ExitGrid exits={view.exits} />
            </CsPanel>
            <CsPanel title={isShips ? "Shipyard Output" : "Shop Output"}>
              <StoryPanel title={isShips ? "Shipyard Output" : "Shop Output"} lines={view.storyLines} />
            </CsPanel>
          </>
        }
        right={
          <CsPanel title={isShips ? "Ships for Sale" : "Items for Sale"}>
            <ul className="mt-1 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {catalog.map((entry) => {
                const rowBusy = busyKey === entry.id;
                const expanded = expandedIds.has(entry.id);
                return (
                  <li key={entry.id} className="rounded border border-cyan-900/30 p-2">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <span className="text-sm font-medium text-zinc-200">{entry.key}</span>
                      <span className="text-[12px] text-zinc-500">
                        {entry.price != null ? `${entry.price.toLocaleString()} cr` : "N/A"}
                      </span>
                      <button
                        type="button"
                        className="inline-flex shrink-0 items-center justify-center rounded border border-cyan-700/50 p-1 text-cyan-400 hover:bg-cyan-950/40"
                        aria-expanded={expanded}
                        aria-label={expanded ? "Hide details" : "Show details"}
                        onClick={() => toggleExpanded(entry.id)}
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 20 20"
                          fill="currentColor"
                          className={`h-4 w-4 transition-transform ${expanded ? "rotate-90" : ""}`}
                          aria-hidden
                        >
                          <path
                            fillRule="evenodd"
                            d="M8.22 5.22a.75.75 0 011.06 0l4.25 4.25a.75.75 0 010 1.06l-4.25 4.25a.75.75 0 01-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 010-1.06z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </button>
                    </div>
                    {expanded ? (
                      <>
                        {entry.description ? <p className="mt-0.5 text-[12px] text-zinc-400">{entry.description}</p> : null}
                        {entry.summary ? <p className="mt-0.5 text-[12px] text-zinc-500">{entry.summary}</p> : null}
                        <div className="mt-1 flex gap-1.5">
                          <button
                            type="button"
                            className="rounded border border-cyan-700/50 px-2 py-0.5 text-[12px] text-cyan-400 disabled:text-cyan-500/50"
                            disabled={rowBusy}
                            onClick={() => onInspect(entry.id, entry.key)}
                          >
                            {rowBusy && busyAction === "inspect" ? "…" : "Inspect"}
                          </button>
                          <button
                            type="button"
                            className="rounded border border-cyan-700/50 bg-cyan-950/40 px-2 py-0.5 text-[12px] text-cyan-400 hover:bg-cyan-900/50 disabled:opacity-60"
                            disabled={rowBusy}
                            onClick={() => onBuy(entry.id, entry.key)}
                          >
                            {rowBusy && busyAction === "buy" ? "…" : "Buy"}
                          </button>
                        </div>
                      </>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </CsPanel>
        }
      />
    </CsPage>
  );
}

export default function ShopPage() {
  return (
    <Suspense
      fallback={
        <main className="main-content">
          <p className="text-sm text-zinc-500 dark:text-cyan-500/80">Loading shop state…</p>
        </main>
      }
    >
      <ShopPageInner />
    </Suspense>
  );
}
