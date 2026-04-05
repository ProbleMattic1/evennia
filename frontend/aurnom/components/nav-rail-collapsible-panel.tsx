"use client";

import { useEffect, useState, type ReactNode } from "react";

import { PanelExpandButton } from "@/components/panel-expand-button";

/** Collapsible rail section — matches Destinations / Character (`aurnom:nav-panel:*` session keys). */
export function NavRailCollapsiblePanel({
  panelKey,
  title,
  children,
  className = "",
  bodyClassName = "border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-xs",
}: {
  panelKey: string;
  title: string;
  children: ReactNode;
  className?: string;
  /** Use `pl-0` when a drag-handle column sits flush left (e.g. Destinations). */
  bodyClassName?: string;
}) {
  const storageKey = `aurnom:nav-panel:${panelKey}`;
  const [open, setOpen] = useState(true);

  useEffect(() => {
    /* sessionStorage is only available after mount; avoids SSR/client mismatch on first paint. */
    /* eslint-disable react-hooks/set-state-in-effect */
    try {
      const raw = window.sessionStorage.getItem(storageKey);
      if (raw !== null) setOpen(raw === "1");
    } catch {
      // ignore
    }
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [storageKey]);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(storageKey, open ? "1" : "0");
    } catch {
      // ignore storage errors and keep UI functional
    }
  }, [open, storageKey]);

  return (
    <section className={`mb-1 ${className}`}>
      <div className="flex items-center bg-cyan-900/30 px-1.5 py-0.5 text-xs font-bold uppercase tracking-widest">
        <span className="text-cyber-cyan">{title}</span>
        <PanelExpandButton
          open={open}
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="ml-auto shrink-0"
        />
      </div>
      {open ? <div className={bodyClassName}>{children}</div> : null}
    </section>
  );
}

/** Shared chrome for rail list rows (Destinations buttons, Services links). */
export const NAV_RAIL_DESTINATION_ROW_CORE =
  "truncate rounded border border-cyan-800/60 px-1 py-0.5 text-left text-xs text-cyber-cyan hover:bg-cyan-900/40 disabled:opacity-40";

/** Full-width row (matches `NavDestinationRow`). */
export const NAV_RAIL_DESTINATION_ROW_CLASS = `block w-full ${NAV_RAIL_DESTINATION_ROW_CORE}`;
