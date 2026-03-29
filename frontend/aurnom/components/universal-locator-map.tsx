"use client";

import "@xyflow/react/dist/style.css";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { LocatorFlattenedView } from "@/components/locator-flattened-view";
import { LocatorGraphView } from "@/components/locator-graph-view";
import { LocatorGridView } from "@/components/locator-grid-view";
import { fetchWorldGraph, getPlayState, playTravel, type WorldGraphState } from "@/lib/ui-api";

const LOCATOR_MODE_STORAGE_KEY = "aurnom:locator-view-mode";

export type LocatorViewMode = "graph" | "flattened" | "grid";

function readStoredMode(): LocatorViewMode {
  if (typeof window === "undefined") return "graph";
  const v = window.localStorage.getItem(LOCATOR_MODE_STORAGE_KEY);
  if (v === "flattened" || v === "grid" || v === "graph") return v;
  return "graph";
}

const MODE_TABS: { id: LocatorViewMode; label: string; hint: string }[] = [
  { id: "graph", label: "Graph", hint: "Dimensional map" },
  { id: "flattened", label: "List", hint: "Flat directory — easier for screen readers" },
  { id: "grid", label: "Districts", hint: "Zoned grid — property & districts" },
];

export function UniversalLocatorMap() {
  const router = useRouter();
  const [data, setData] = useState<WorldGraphState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [schematic, setSchematic] = useState(false);
  const [filter, setFilter] = useState("");
  const [travelBusy, setTravelBusy] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [mode, setMode] = useState<LocatorViewMode>("graph");
  const skipFirstPersist = useRef(true);

  useEffect(() => {
    setMode(readStoredMode());
  }, []);

  useEffect(() => {
    if (skipFirstPersist.current) {
      skipFirstPersist.current = false;
      return;
    }
    try {
      window.localStorage.setItem(LOCATOR_MODE_STORAGE_KEY, mode);
    } catch {
      // ignore quota / private mode
    }
  }, [mode]);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mq.matches);
    const fn = () => setReduceMotion(mq.matches);
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, []);

  const load = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const g = await fetchWorldGraph();
      setData(g);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load map");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const id = window.setInterval(() => load(), 45_000);
    return () => window.clearInterval(id);
  }, [load]);

  const reachableSet = useMemo(() => {
    if (!data?.reachableRoomIds) return null;
    return new Set(data.reachableRoomIds);
  }, [data?.reachableRoomIds]);

  const adjacentSet = useMemo(() => {
    if (!data?.adjacentRoomKeys) return null;
    return new Set(data.adjacentRoomKeys);
  }, [data?.adjacentRoomKeys]);

  const tryTravelTo = useCallback(
    async (roomKey: string) => {
      if (!adjacentSet?.has(roomKey) || travelBusy) return;
      setTravelBusy(true);
      setError(null);
      try {
        await playTravel({ destination: roomKey });
        const goHome = () => router.push("/");
        if (!reduceMotion && typeof document !== "undefined" && document.startViewTransition) {
          document.startViewTransition(goHome);
        } else {
          goHome();
        }
      } catch (e) {
        setTravelBusy(false);
        setError(e instanceof Error ? e.message : "Travel failed");
      }
    },
    [adjacentSet, travelBusy, reduceMotion, router],
  );

  const prefetchRoom = useCallback((roomKey: string) => {
    void getPlayState(roomKey).catch(() => {});
  }, []);

  if (loading && !data) {
    return (
      <div className="rounded border border-cyan-900/50 bg-zinc-950 p-4 font-mono text-[11px] text-cyan-300">
        Loading station graph…
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="rounded border border-red-900/50 bg-zinc-950 p-4 font-mono text-[11px] text-red-400">
        {error}
        <button
          type="button"
          className="ml-2 text-cyan-400 underline"
          onClick={() => void load()}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="flex min-w-0 flex-col gap-2">
      {error ? (
        <div
          className="rounded border border-red-900/50 bg-red-950/40 px-2 py-1 font-mono text-[11px] text-red-300"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] text-ui-muted">
        <span>
          Snapshot:{" "}
          <time dateTime={data.generatedAt} className="text-zinc-300">
            {new Date(data.generatedAt).toLocaleString()}
          </time>
        </span>
        {refreshing ? <span className="text-cyan-300">Refreshing…</span> : null}
        <div
          className="ml-auto flex flex-wrap items-center gap-1"
          role="tablist"
          aria-label="Locator view mode"
        >
          {MODE_TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={mode === t.id}
              title={t.hint}
              className={[
                "rounded border px-2 py-0.5 text-[10px] uppercase tracking-wide",
                mode === t.id
                  ? "border-cyan-500 bg-cyan-950/60 text-cyan-300"
                  : "border-cyan-900/50 text-ui-muted hover:border-cyan-800 hover:text-ui-soft",
              ].join(" ")}
              onClick={() => setMode(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
        {mode === "graph" ? (
          <label className="flex cursor-pointer items-center gap-1 text-ui-muted">
            <input
              type="checkbox"
              checked={schematic}
              onChange={(e) => setSchematic(e.target.checked)}
              className="accent-cyan-600"
            />
            Full topology (hidden links)
          </label>
        ) : null}
        <button
          type="button"
          className="rounded border border-cyan-800/60 px-2 py-0.5 text-cyan-400 hover:bg-cyan-950/50"
          onClick={() => void load()}
        >
          Refresh now
        </button>
      </div>

      <input
        type="search"
        placeholder="Filter rooms…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="w-full max-w-sm rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1 font-mono text-[11px] text-zinc-200 placeholder:text-ui-soft"
        aria-label="Filter rooms"
      />

      <div role="tabpanel" aria-label={MODE_TABS.find((m) => m.id === mode)?.label ?? "Locator"}>
        {mode === "graph" ? (
          <LocatorGraphView
            data={data}
            filter={filter}
            schematic={schematic}
            reduceMotion={reduceMotion}
            adjacentKeys={adjacentSet}
            reachableIds={reachableSet}
            travelBusy={travelBusy}
            onTravelTo={tryTravelTo}
            onPrefetchRoom={prefetchRoom}
          />
        ) : null}
        {mode === "flattened" ? (
          <LocatorFlattenedView
            data={data}
            filter={filter}
            adjacentKeys={adjacentSet}
            reachableIds={reachableSet}
            travelBusy={travelBusy}
            onTravelTo={tryTravelTo}
            onPrefetchRoom={prefetchRoom}
          />
        ) : null}
        {mode === "grid" ? (
          <LocatorGridView
            data={data}
            filter={filter}
            adjacentKeys={adjacentSet}
            reachableIds={reachableSet}
            travelBusy={travelBusy}
            onTravelTo={tryTravelTo}
            onPrefetchRoom={prefetchRoom}
          />
        ) : null}
      </div>
    </div>
  );
}

export function LocatorPageChrome({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-svh bg-zinc-950 p-3 font-mono text-[11px] text-zinc-300 md:p-6">
      <header className="mb-4 border-b border-cyan-900/40 pb-3">
        <div className="flex flex-wrap items-baseline gap-3">
          <h1 className="text-sm font-bold uppercase tracking-widest text-cyan-400">
            Universal Locator
          </h1>
          <span className="text-ui-muted">Interactive station map</span>
          <Link
            href="/"
            className="ml-auto rounded border border-cyan-800/60 px-2 py-1 text-cyan-400 hover:bg-cyan-950/50"
          >
            ← Control surface
          </Link>
        </div>
        <nav className="mt-2" aria-label="Locator related">
          <Link
            href="/economy"
            className="inline-block rounded border border-cyan-800/60 px-2 py-0.5 text-[10px] text-cyan-400 hover:bg-cyan-950/50"
          >
            Economy
          </Link>
        </nav>
      </header>
      {children}
    </main>
  );
}
