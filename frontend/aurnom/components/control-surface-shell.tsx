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
    <div className="dark min-h-svh bg-zinc-950 font-mono text-xs text-foreground">
      <div
        className={
          "mx-auto grid min-h-svh w-full max-w-[400px] grid-cols-1 " +
          "md:max-w-[800px] md:max-[1199px]:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_minmax(0,2fr)] " +
          "lg:max-w-[1200px] min-[1200px]:grid-cols-[200px_minmax(0,1fr)]"
        }
      >
        <PersistentNavRail />
        <div className="min-w-0 md:max-[1199px]:col-span-2 min-[1200px]:col-span-1">
          <ControlSurfaceMainPanels data={data} onReload={onReload} />
        </div>
      </div>
    </div>
  );
}
