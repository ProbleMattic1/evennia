"use client";

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
import { useEffect, useMemo } from "react";

import { HUB_ROOM_KEY } from "@/lib/locator-zones";
import type { WorldGraphEdge, WorldGraphRoom, WorldGraphState } from "@/lib/ui-api";

/** Matches `game/world/bootstrap_frontier.py` */
const FRONTIER_PROMENADE_KEY = "Frontier Promenade";

const NANOMASS_CENTER = { x: 0, y: 0 };
const FRONTIER_MASS_CENTER = { x: 1100, y: 0 };
/** Contractor / industrial grids (plex + Ashfall NPC pads), separate from promenade masses */
const INDUSTRIAL_MASS_CENTER = { x: 550, y: 520 };

function isIndustrialMassRoom(r: WorldGraphRoom): boolean {
  const z = r.locatorZone;
  if (z === "plex-industrial" || z === "ashfall-industrial") return true;
  const k = r.key;
  return (
    k === "Ashfall Industrial Grid" ||
    k.startsWith("Ashfall Industrial Pad ") ||
    k === "NanoMegaPlex Industrial Subdeck" ||
    k.startsWith("NanoMegaPlex Industrial Pad ") ||
    k === "Frontier Industrial Subdeck" ||
    k.startsWith("Frontier Industrial Pad ")
  );
}

function clusterForRoom(r: WorldGraphRoom): "nano" | "frontier" | "industrial" {
  if (isIndustrialMassRoom(r)) return "industrial";
  if (r.venueId === "frontier_outpost") return "frontier";
  if (r.venueId === "nanomega_core") return "nano";
  const k = r.key;
  if (k === "Frontier Transit Shell" || k.startsWith("Frontier ")) return "frontier";
  return "nano";
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

function layoutPosition(r: WorldGraphRoom): { x: number; y: number } {
  if (r.key === HUB_ROOM_KEY) return { ...NANOMASS_CENTER };
  if (r.key === FRONTIER_PROMENADE_KEY) return { ...FRONTIER_MASS_CENTER };

  const cl = clusterForRoom(r);
  const center =
    cl === "frontier" ? FRONTIER_MASS_CENTER : cl === "industrial" ? INDUSTRIAL_MASS_CENTER : NANOMASS_CENTER;
  const k = r.key;
  let h = 0;
  for (let i = 0; i < k.length; i++) {
    h = (h * 31 + k.charCodeAt(i)) >>> 0;
  }
  const angle = ((h % 360) * Math.PI) / 180;
  const radiusBase = cl === "industrial" ? 100 : 130;
  const radiusStep = cl === "industrial" ? 48 : 52;
  const radius = radiusBase + (h % 6) * radiusStep;
  return {
    x: center.x + Math.cos(angle) * radius,
    y: center.y + Math.sin(angle) * radius,
  };
}

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

function massConnectorEdge(rooms: WorldGraphRoom[]): Edge | null {
  let nanoId: string | undefined;
  let frontierId: string | undefined;
  for (const r of rooms) {
    if (r.key === HUB_ROOM_KEY) nanoId = String(r.id);
    else if (r.key === FRONTIER_PROMENADE_KEY) frontierId = String(r.id);
  }
  if (!nanoId || !frontierId) return null;
  return {
    id: "locator-mass-connector",
    source: nanoId,
    target: frontierId,
    type: "straight",
    selectable: false,
    focusable: false,
    interactionWidth: 0,
    animated: false,
    style: {
      stroke: "#a78bfa",
      strokeWidth: 2.5,
      strokeDasharray: "12 8",
      opacity: 0.9,
    },
    markerEnd: undefined,
    zIndex: 0,
  };
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
      const pos = layoutPosition(r);
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

export type LocatorGraphViewProps = {
  data: WorldGraphState;
  filter: string;
  schematic: boolean;
  reduceMotion: boolean;
  adjacentKeys: Set<string> | null;
  reachableIds: Set<number> | null;
  travelBusy: boolean;
  onTravelTo: (roomKey: string) => void;
  onPrefetchRoom: (roomKey: string) => void;
};

export function LocatorGraphView({
  data,
  filter,
  schematic,
  reduceMotion,
  adjacentKeys,
  reachableIds,
  travelBusy,
  onTravelTo,
  onPrefetchRoom,
}: LocatorGraphViewProps) {
  const nodes: Node[] = useMemo(
    () =>
      buildFlowNodes(
        data.rooms,
        filter,
        data.currentRoomKey,
        reachableIds,
        adjacentKeys,
      ),
    [data.rooms, data.currentRoomKey, filter, reachableIds, adjacentKeys],
  );

  const edges: Edge[] = useMemo(() => {
    const base = buildFlowEdges(data.edges, data.edgesAll, schematic, reduceMotion);
    const q = filter.trim().toLowerCase();
    const visibleRooms = q
      ? data.rooms.filter((r) => r.key.toLowerCase().includes(q))
      : data.rooms;
    const spine = massConnectorEdge(visibleRooms);
    return spine ? [spine, ...base] : base;
  }, [data.rooms, data.edges, data.edgesAll, schematic, reduceMotion, filter]);

  return (
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
          onNodeClick={(_, node) => {
            const key = (node.data as LocatorNodeData).roomKey;
            if (!adjacentKeys?.has(key) || travelBusy) return;
            onTravelTo(key);
          }}
          onNodeMouseEnter={(_, node) => {
            onPrefetchRoom((node.data as LocatorNodeData).roomKey);
          }}
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
          <Panel position="top-left" className="m-2 max-w-[280px] text-[10px] text-zinc-500">
            Three clusters: <span className="text-cyan-400">NanoMegaPlex</span> (coreward),{" "}
            <span className="text-violet-400">Frontier</span> (rim), and{" "}
            <span className="text-amber-400">industrial mines</span> (plex + Ashfall contractor grids). The dashed{" "}
            <span className="text-violet-300">violet</span> line links the two promenades only (not travel). Click{" "}
            <span className="text-cyan-400">Go</span> for cyan exits. Hub mining routes stay off the cyan graph unless
            Full topology is on.
          </Panel>
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
