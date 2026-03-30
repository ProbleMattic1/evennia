"use client";

import Link from "next/link";
import { useMemo } from "react";

import type { ExitButton } from "@/lib/ui-api";

type Props = {
  exits: ExitButton[];
};

export function groupExits(exits: ExitButton[]) {
  const map = new Map<
    string,
    { order: number; sectionOrder: number; items: ExitButton[] }
  >();
  for (const ex of exits) {
    const title = ex.section ?? "Destinations";
    const prev = map.get(title);
    const sectionOrder = ex.sectionOrder ?? 999;
    const rowOrder = ex.order ?? 0;
    if (!prev) {
      map.set(title, { order: sectionOrder, sectionOrder, items: [ex] });
    } else {
      prev.items.push(ex);
      prev.order = Math.min(prev.order, sectionOrder);
    }
  }
  for (const g of map.values()) {
    g.items.sort(
      (a, b) =>
        (a.order ?? 0) - (b.order ?? 0) ||
        a.label.localeCompare(b.label, undefined, { sensitivity: "base" }),
    );
  }
  return [...map.entries()]
    .sort((a, b) => a[1].order - b[1].order || a[0].localeCompare(b[0]))
    .map(([title, g]) => ({ title, items: g.items }));
}

export function ExitGrid({ exits }: Props) {
  const groups = useMemo(() => groupExits(exits), [exits]);

  if (groups.length <= 1 && (groups[0]?.title === "Destinations" || !groups[0])) {
    return (
      <div className="flex flex-wrap gap-1">
        {exits.map((exit) => (
          <Link
            key={`${exit.key}-${exit.destination ?? "none"}`}
            href="/"
            className="rounded border border-cyan-800/60 px-2 py-1 text-[11px] text-cyan-400 hover:bg-cyan-900/40 hover:text-cyan-300"
          >
            {exit.label}
          </Link>
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {groups.map(({ title, items }) => (
        <div key={title}>
          <div className="mb-0.5 text-[10px] uppercase tracking-wide text-ui-muted">{title}</div>
          <div className="flex flex-wrap gap-1">
            {items.map((exit) => (
              <Link
                key={`${exit.key}-${exit.destination ?? "none"}`}
                href="/"
                className="rounded border border-cyan-800/60 px-2 py-1 text-[11px] text-cyan-400 hover:bg-cyan-900/40 hover:text-cyan-300"
              >
                {exit.label}
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
