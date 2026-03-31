"use client";

import { createContext, useCallback, useContext, useEffect, useMemo } from "react";

import { PersistentNavRail } from "@/components/persistent-nav-rail";
import { getControlSurfaceState, type ControlSurfaceState } from "@/lib/control-surface-api";
import { intervalMs, isUiPollPaused } from "@/lib/ui-refresh-policy";
import { useUiResource } from "@/lib/use-ui-resource";

type ControlSurfaceContextValue = {
  data: ControlSurfaceState | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
};

const ControlSurfaceContext = createContext<ControlSurfaceContextValue | null>(null);

export function useControlSurface(): ControlSurfaceContextValue {
  const value = useContext(ControlSurfaceContext);
  if (!value) {
    throw new Error("useControlSurface must be used within ControlSurfaceProvider.");
  }
  return value;
}

export function ControlSurfaceProvider({ children }: { children: React.ReactNode }) {
  const loader = useCallback(() => getControlSurfaceState(), []);
  const { data, error, loading, reload } = useUiResource(loader);

  useEffect(() => {
    const ms = intervalMs("controlSurface", data?.clientPollHints);
    const id = setInterval(() => {
      if (!isUiPollPaused()) reload();
    }, ms);
    return () => clearInterval(id);
  }, [reload, data?.clientPollHints]);

  const value = useMemo(
    () => ({ data, loading, error, reload }),
    [data, loading, error, reload],
  );

  return (
    <ControlSurfaceContext.Provider value={value}>
      <div
        className={
          "dark mx-auto grid min-h-svh w-full max-w-[400px] grid-cols-1 bg-zinc-950 font-mono text-xs text-foreground " +
          "md:max-w-[800px] md:grid-cols-[minmax(0,1fr)_minmax(0,2fr)_minmax(0,2fr)] " +
          "lg:max-w-[1200px]"
        }
      >
        <PersistentNavRail />
        <main className="min-h-0 min-w-0 bg-zinc-950 md:col-span-2">{children}</main>
      </div>
    </ControlSurfaceContext.Provider>
  );
}
