"use client";

import { createContext, useCallback, useContext, useEffect, useMemo } from "react";

import { PersistentNavRail } from "@/components/persistent-nav-rail";
import { getControlSurfaceState, type ControlSurfaceState } from "@/lib/control-surface-api";
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
    const id = setInterval(reload, 15_000);
    return () => clearInterval(id);
  }, [reload]);

  const value = useMemo(
    () => ({ data, loading, error, reload }),
    [data, loading, error, reload],
  );

  return (
    <ControlSurfaceContext.Provider value={value}>
      <div
        className="dark mx-auto grid min-h-svh w-[85%] bg-zinc-950 font-mono text-xs text-foreground"
        style={{ gridTemplateColumns: "minmax(12rem,20%) minmax(20rem,40%) minmax(20rem,40%)" }}
      >
        <PersistentNavRail />
        <main className="col-span-2 min-w-0">{children}</main>
      </div>
    </ControlSurfaceContext.Provider>
  );
}
