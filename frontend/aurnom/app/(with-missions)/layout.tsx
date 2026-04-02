"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";

import { DashboardMissionsPanel, EMPTY_MISSIONS } from "@/components/dashboard-missions-panel";
import { useControlSurface } from "@/components/control-surface-provider";
import { useMsgStream } from "@/lib/use-msg-stream";

export default function WithMissionsLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
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
  );
}
