"use client";

import "@xyflow/react/dist/style.css";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Background,
  Controls,
  type Edge,
  MarkerType,
  MiniMap,
  type Node,
  NodeProps,
  Panel,
  Position,
  ReactFlow,
  ReactFlowProvider,
  Handle,
  useReactFlow,
} from "@xyflow/react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  fetchWorldGraph,
  getPlayState,
  playTravel,
  type WorldGraphEdge,
  type WorldGraphRoom,
  type WorldGraphState,
} from "@/lib/ui-api";

const HUB_ROOM_KEY = "NanoMegaPlex Promenade";

function layoutPosition(roomKey: string): { x: number; y: number } {
  if (roomKey === HUB_ROOM_KEY) return { x: 0, y: 0 };
  let h = 0;
  for (let i = 0; i < roomKey.length; i++) {
    h = (h * 31 + roomKey.charCodeAt(i)) >>> 0;
  }
  const angle = ((h % 360) * Math.PI) / 180;
  const radius = 380 + (h % 7) * 95;
  return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius };
}

type LocatorNodeData = {
  label: string;
  roomKey: string;
  here: boolean;
  reachable: boolean;
  canStep: boolean;
  hasMiningSite: boolean;
  dim: boolean;
};

function LocatorNode({ data }: NodeProps) {
  const d = data as LocatorNodeData;
  return (
    <>
      <Handle type="target" position={Position.Left} className="!bg-cyan-600" />
      <div
        className={[
          "max-w-[160px] rounded-md border px-2 py-1.5 text-left shadow-sm",
          d.here
            ? "border-amber-500 bg-amber-950/90 ring-2 ring-amber-400/80"
            : d.canStep
              ? "cursor-pointer border-cyan-500 bg-cyan-950/80 hover:bg-cyan-900/80"
              : d.reachable
                ? "border-cyan-800/60 bg-zinc-900/90"
                : "border-zinc-700 bg-zinc-950/90",
          d.dim ? "opacity-40" : "",
        ].join(" ")}
      >
        <div className="truncate font-mono text-[10px] font-semibold text-zinc-100">{d.label}</div>
        <div className="mt-0.5 flex flex-wrap gap-1">
          {d.here ? (
            <span className="rounded bg-amber-900/50 px-1 text-[9px] uppercase text-amber-200">You</span>
          ) : null}
          {d.hasMiningSite ? (
            <span className="rounded bg-amber-950/80 px-1 text-[9px] text-amber-500/90">Mine</span>
          ) : null}
          {d.canStep ? (
            <span className="rounded bg-cyan-900/40 px-1 text-[9px] text-cyan-300">Go</span>
          ) : null}
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-cyan-600" />
    </>
  );
}

const nodeTypes = { locator: LocatorNode };

function edgeSignature(e: WorldGraphEdge): string {
  return `${e.fromId}-${e.toId}-${e.exitKey}`;
}

function buildFlowEdges(
  visible: WorldGraphEdge[],
  all: WorldGraphEdge[],
  schematic: boolean,
  reduceMotion: boolean,
): Edge[] {
  const visibleSig = new Set(visible.map(edgeSignature));
  const out: Edge[] = [];

  if (schematic) {
    for (const e of all) {
      if (visibleSig.has(edgeSignature(e))) continue;
      out.push({
        id: `ghost-${e.fromId}-${e.toId}-${e.exitKey}`,
        source: String(e.fromId),
        target: String(e.toId),
        selectable: false,
        focusable: false,
        interactionWidth: 0,
        animated: false,
        style: {
          stroke: "#64748b",
          strokeWidth: 1,
          opacity: 0.35,
        },
        markerEnd: undefined,
      });
    }
  }

  for (const e of visible) {
    out.push({
      id: `e-${e.fromId}-${e.toId}-${e.exitKey}`,
      source: String(e.fromId),
      target: String(e.toId),
      animated: !reduceMotion,
      style: { stroke: "#22d3ee", strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#22d3ee", width: 16, height: 16 },
    });
  }

  return out;
}

function buildFlowNodes(
  rooms: WorldGraphRoom[],
  filter: string,
  currentRoomKey: string | null,
  reachableIds: Set<number> | null,
  adjacentKeys: Set<string> | null,
): Node[] {
  const q = filter.trim().toLowerCase();
  return rooms
    .filter((r) => !q || r.key.toLowerCase().includes(q))
    .map((r) => {
      const reachable = reachableIds ? reachableIds.has(r.id) : true;
      const canStep = adjacentKeys ? adjacentKeys.has(r.key) : false;
      const here = currentRoomKey === r.key;
      const dim = reachableIds ? !reachable : false;
      const pos = layoutPosition(r.key);
      return {
        id: String(r.id),
        type: "locator",
        position: pos,
        data: {
          label: r.key,
          roomKey: r.key,
          here,
          reachable,
          canStep,
          hasMiningSite: r.hasMiningSite,
          dim: dim && !here,
        } satisfies LocatorNodeData,
      };
    });
}

function FitViewOnChange({ deps }: { deps: unknown }) {
  const rf = useReactFlow();
  useEffect(() => {
    const id = window.setTimeout(() => {
      rf.fitView({ padding: 0.15, duration: 200 });
    }, 80);
    return () => window.clearTimeout(id);
  }, [rf, deps]);
  return null;
}

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

  const nodes: Node[] = useMemo(() => {
    if (!data?.rooms) return [];
    return buildFlowNodes(
      data.rooms,
      filter,
      data.currentRoomKey,
      reachableSet,
      adjacentSet,
    );
  }, [data, filter, reachableSet, adjacentSet]);

  const edges: Edge[] = useMemo(() => {
    if (!data) return [];
    return buildFlowEdges(data.edges, data.edgesAll, schematic, reduceMotion);
  }, [data, schematic, reduceMotion]);

  const onNodeClick = useCallback(
    async (_: React.MouseEvent, node: Node) => {
      const key = (node.data as LocatorNodeData).roomKey;
      if (!adjacentSet?.has(key) || travelBusy) return;
      setTravelBusy(true);
      setError(null);
      try {
        await playTravel({ destination: key });
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

  const onNodeMouseEnter = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const key = (node.data as LocatorNodeData).roomKey;
      void getPlayState(key).catch(() => {});
    },
    [],
  );

  if (loading && !data) {
    return (
      <div className="rounded border border-cyan-900/50 bg-zinc-950 p-4 font-mono text-[11px] text-cyan-500">
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
        <div className="rounded border border-red-900/50 bg-red-950/40 px-2 py-1 font-mono text-[11px] text-red-300">
          {error}
        </div>
      ) : null}
      <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] text-zinc-400">
        <span>
          Snapshot:{" "}
          <time dateTime={data.generatedAt} className="text-zinc-300">
            {new Date(data.generatedAt).toLocaleString()}
          </time>
        </span>
        {refreshing ? <span className="text-cyan-500">Refreshing…</span> : null}
        <label className="ml-auto flex cursor-pointer items-center gap-1 text-zinc-400">
          <input
            type="checkbox"
            checked={schematic}
            onChange={(e) => setSchematic(e.target.checked)}
            className="accent-cyan-600"
          />
          Full topology (hidden links)
        </label>
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
        className="w-full max-w-sm rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1 font-mono text-[11px] text-zinc-200 placeholder:text-zinc-600"
        aria-label="Filter rooms"
      />
      {/* React Flow requires explicit width + height on the parent (not only min-height). */}
      <div className="h-[min(60vh,640px)] w-full min-h-[320px] rounded border border-cyan-900/40 bg-zinc-950">
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.08}
            maxZoom={1.5}
            proOptions={{ hideAttribution: true }}
            onNodeClick={onNodeClick}
            onNodeMouseEnter={onNodeMouseEnter}
            className="locator-flow h-full w-full bg-zinc-950 dark"
          >
            <Background color="#164e63" gap={20} size={1} />
            <Controls className="!shadow-none" showInteractive={false} />
            <MiniMap
              className="locator-minimap !m-2 rounded border border-cyan-900/40 !shadow-none"
              style={{ width: 128, height: 84 }}
              nodeStrokeWidth={1}
              maskColor="rgba(9, 9, 11, 0.72)"
              pannable
              zoomable
              aria-label="Overview map"
            />
            <FitViewOnChange deps={`${nodes.length}-${edges.length}-${schematic}-${filter}`} />
            <Panel position="top-left" className="m-2 max-w-[240px] text-[10px] text-zinc-500">
              Click a node marked <span className="text-cyan-400">Go</span> to travel one hop. Hub mining
              routes you cannot use stay off the cyan graph unless Full topology is on. Lower right: small{" "}
              <span className="text-zinc-400">overview map</span> (viewport); drag it to pan.
            </Panel>
          </ReactFlow>
        </ReactFlowProvider>
      </div>
    </div>
  );
}

export function LocatorPageChrome({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-svh bg-zinc-950 p-3 font-mono text-[11px] text-zinc-300 md:p-6">
      <header className="mb-4 flex flex-wrap items-baseline gap-3 border-b border-cyan-900/40 pb-3">
        <h1 className="text-sm font-bold uppercase tracking-widest text-cyan-400">
          Universal Locator
        </h1>
        <span className="text-zinc-500">Interactive station map</span>
        <Link
          href="/"
          className="ml-auto rounded border border-cyan-800/60 px-2 py-1 text-cyan-400 hover:bg-cyan-950/50"
        >
          ← Control surface
        </Link>
      </header>
      {children}
    </main>
  );
}
