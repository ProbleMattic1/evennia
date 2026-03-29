"use client";

import { ControlSurfaceMainPanels } from "@/components/control-surface-main-panels";
import { useControlSurface } from "@/components/control-surface-provider";

export default function HomePage() {
  const { data, error, loading, reload } = useControlSurface();

  if (loading && !data) {
    return (
      <main className="dark min-h-svh bg-zinc-950 p-2 font-mono text-[11px] text-cyan-400">
        Loading control surface…
      </main>
    );
  }

  if (error && !data) {
    return (
      <main className="dark min-h-svh bg-zinc-950 p-2 font-mono text-[11px] text-red-400">
        Failed to load: {error}
      </main>
    );
  }

  if (!data) {
    return (
      <main className="dark min-h-svh bg-zinc-950 p-2 font-mono text-[11px] text-ui-muted">
        No data.
      </main>
    );
  }

  return <ControlSurfaceMainPanels data={data} onReload={reload} />;
}
