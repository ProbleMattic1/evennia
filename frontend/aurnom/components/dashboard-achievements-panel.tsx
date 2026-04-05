"use client";

import { useState } from "react";

import { PanelExpandButton } from "@/components/panel-expand-button";
import type { CsAchievementsBlock } from "@/lib/control-surface-api";
import {
  DASHBOARD_PANEL_BODY,
  DASHBOARD_PANEL_HEADER,
  DASHBOARD_PANEL_SECTION,
  DASHBOARD_PANEL_TITLE,
} from "@/lib/dashboard-panel-chrome";

const STORAGE_KEY = "aurnom:dashboard-panel:achievements";

type Props = {
  achievements?: CsAchievementsBlock | null;
};

/**
 * Character milestones; rendered directly below World status on the dashboard missions column.
 */
export function DashboardAchievementsPanel({ achievements = null }: Props) {
  const [open, setOpen] = useState(() => {
    if (typeof window === "undefined") return true;
    try {
      const raw = window.sessionStorage.getItem(STORAGE_KEY);
      return raw == null ? true : raw === "1";
    } catch {
      return true;
    }
  });

  function toggleOpen() {
    setOpen((v) => {
      const next = !v;
      try {
        window.sessionStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      } catch {
        // ignore storage failures
      }
      return next;
    });
  }

  return (
    <section className={DASHBOARD_PANEL_SECTION}>
      <div className={DASHBOARD_PANEL_HEADER}>
        <span className={DASHBOARD_PANEL_TITLE}>Achievements</span>
        <PanelExpandButton
          open={open}
          onClick={toggleOpen}
          aria-label={`${open ? "Collapse" : "Expand"} Achievements`}
          className="ml-auto shrink-0"
        />
      </div>

      {open ? (
        <div className={DASHBOARD_PANEL_BODY}>
          {achievements != null && achievements.items.length > 0 ? (
            <>
              <div className="mb-2 font-mono text-[10px] text-zinc-400">
                Completed {achievements.completed} / {achievements.total}
              </div>
              <ul className="flex max-h-64 flex-col gap-2 overflow-y-auto pr-0.5">
                {achievements.items.map((row) => (
                  <li
                    key={row.key}
                    className="rounded-md border border-zinc-800/55 bg-zinc-950/45 px-2 py-1.5"
                  >
                    <div className="flex min-w-0 items-start justify-between gap-2">
                      <span
                        className={`min-w-0 truncate text-[11px] font-semibold leading-tight ${
                          row.completed ? "text-cyber-cyan/95" : "text-zinc-200"
                        }`}
                      >
                        {row.name}
                      </span>
                      <span className="shrink-0 font-mono text-[10px] tabular-nums text-zinc-400">
                        {row.completed ? "Done" : row.locked ? "Locked" : `${row.progress} / ${row.target}`}
                      </span>
                    </div>
                    {row.category ? (
                      <div className="mt-0.5 text-[9px] font-semibold uppercase tracking-wide text-zinc-500">
                        {row.category}
                      </div>
                    ) : null}
                    {row.desc ? (
                      <p className="mt-1 text-[10px] leading-snug text-ui-muted">{row.desc}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-[11px] text-ui-muted">
              {achievements != null
                ? "No milestones defined yet."
                : "Sign in with a character to see milestones."}
            </p>
          )}
        </div>
      ) : null}
    </section>
  );
}
