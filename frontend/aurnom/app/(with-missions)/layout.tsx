"use client";

import { useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";

import { DashboardMissionsPanel, EMPTY_MISSIONS } from "@/components/dashboard-missions-panel";
import { useControlSurface } from "@/components/control-surface-provider";
import { MissionsChromeHeightProvider } from "@/lib/missions-chrome-height-context";
import { WithMissionsProcessingSplitHostsProvider } from "@/lib/with-missions-processing-split";
import { useMsgStream } from "@/lib/use-msg-stream";

export default function WithMissionsLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const isProcessingRoute = pathname === "/processing";
  const { data, loading, error, reload } = useControlSurface();
  const { messages: gameLog } = useMsgStream();

  const onChanged = useCallback(() => {
    reload();
    router.refresh();
  }, [reload, router]);

  if (loading && !data) {
    return (
      <div className="dark min-h-svh bg-zinc-950 p-2 font-mono text-xs text-ui-accent-readable">
        Loading control surface…
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="dark min-h-svh bg-zinc-950 p-2 font-mono text-xs text-red-400">
        Failed to load control surface: {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="dark min-h-svh bg-zinc-950 p-2 font-mono text-xs text-ui-muted">
        No control surface.
      </div>
    );
  }

  return (
    <MissionsChromeHeightProvider>
      <WithMissionsProcessingSplitHostsProvider active={isProcessingRoute}>
        {({ setTopHost, setWideHost, setBelowMissionsHost }) =>
          isProcessingRoute ? (
            <div className="flex min-h-0 min-w-0 flex-col md:min-h-svh md:flex-row md:items-stretch md:overflow-x-hidden">
              <div className="relative z-10 min-h-0 min-w-0 border-b border-cyan-900/40 bg-zinc-950 p-1.5 md:w-1/2 md:flex-shrink-0 md:border-b-0 md:border-r md:overflow-y-auto">
                <DashboardMissionsPanel
                  missions={data.missions ?? EMPTY_MISSIONS}
                  quests={data.quests ?? null}
                  roomExits={data.roomExits}
                  onChanged={onChanged}
                  gameLog={gameLog}
                  setProcessingBelowMissionsHost={setBelowMissionsHost}
                />
              </div>
              <div className="relative z-0 flex min-h-0 min-w-0 flex-1 flex-col md:min-h-0">
                <div
                  ref={setTopHost}
                  className="relative z-10 hidden min-h-0 min-w-0 shrink-0 overflow-y-auto bg-zinc-950 p-1.5 md:block"
                />
                <div
                  ref={setWideHost}
                  className="relative z-0 hidden min-h-0 w-full min-w-0 shrink-0 overflow-x-hidden overflow-y-auto border-y border-cyan-900/40 bg-zinc-950 p-1.5 md:block md:box-border"
                />
                <div className="relative z-10 min-h-0 flex-1 overflow-y-auto bg-zinc-950 p-1.5">{children}</div>
              </div>
            </div>
          ) : (
            <div className="grid min-h-0 grid-cols-1 md:min-h-svh md:grid-cols-2">
              <div className="min-h-0 min-w-0 overflow-y-auto border-r border-cyan-900/40 p-1.5 md:min-h-0">
                <DashboardMissionsPanel
                  missions={data.missions ?? EMPTY_MISSIONS}
                  quests={data.quests ?? null}
                  roomExits={data.roomExits}
                  onChanged={onChanged}
                  gameLog={gameLog}
                />
              </div>
              <div className="min-h-0 min-w-0 overflow-y-auto p-1.5 md:min-h-0">{children}</div>
            </div>
          )
        }
      </WithMissionsProcessingSplitHostsProvider>
    </MissionsChromeHeightProvider>
  );
}
