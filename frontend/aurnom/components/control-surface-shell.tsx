"use client";

import { ControlSurfaceMainPanels } from "@/components/control-surface-main-panels";
import { PersistentNavRail } from "@/components/persistent-nav-rail";
import type { ControlSurfaceState } from "@/lib/control-surface-api";

export function ControlSurfaceShell({
  data,
  onReload,
}: {
  data: ControlSurfaceState;
  onReload: () => void;
}) {
  return (
    <div className="dark min-h-svh bg-zinc-950 font-mono text-[11px] text-zinc-300">
      <div
        className="grid min-h-svh"
        style={{
          gridTemplateColumns: "minmax(12rem,20%) minmax(20rem,40%) minmax(20rem,40%)",
        }}
      >
        <PersistentNavRail />
        <div className="col-span-2 min-w-0">
          <ControlSurfaceMainPanels data={data} onReload={onReload} />
        </div>
      </div>
    </div>
  );
}
