"use client";

import type { ReactNode } from "react";

/**
 * Dense stat card for economy dashboards. Use `title` for full definitions (hover).
 * Keep body content flat — pairs of label + value in a grid or flex.
 */
export function EconomyStatCard({
  title,
  hintTitle,
  headerRight,
  children,
}: {
  title: string;
  /** Longer explanation; shown as native tooltip on hover. */
  hintTitle?: string;
  /** Compact metadata in the header row (e.g. next boundary). */
  headerRight?: ReactNode;
  children: ReactNode;
}) {
  return (
    <article
      className="rounded border border-cyan-900/45 bg-zinc-950/90 px-2.5 py-2 font-mono text-[10px] text-ui-muted"
      title={hintTitle}
    >
      <header className="mb-1.5 flex items-center justify-between gap-2 border-b border-cyan-950/60 pb-1">
        <h2 className="text-[9px] font-bold uppercase tracking-wider text-ui-muted">{title}</h2>
        {headerRight ? <div className="shrink-0">{headerRight}</div> : null}
      </header>
      {children}
    </article>
  );
}
