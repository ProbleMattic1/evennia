"use client";

import { useCallback, useEffect, useMemo } from "react";
import { getMarketState } from "@/lib/ui-api";
import type { MarketCommodity } from "@/lib/ui-api";
import { isUiPollPaused, UI_REFRESH_MS } from "@/lib/ui-refresh-policy";
import { useUiResource } from "@/lib/use-ui-resource";

// ─── Category config ─────────────────────────────────────────────────────────

const CAT: Record<string, { label: string; text: string; badge: string; heading: string }> = {
  standard_metal: {
    label:   "Metal",
    text:    "text-emerald-600 dark:text-emerald-400",
    badge:   "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-400 dark:ring-emerald-700/50",
    heading: "text-emerald-700 dark:text-emerald-400",
  },
  exotic_metal: {
    label:   "Exotic",
    text:    "text-amber-600 dark:text-amber-400",
    badge:   "bg-amber-100 text-amber-800 ring-1 ring-amber-300 dark:bg-amber-950 dark:text-amber-400 dark:ring-amber-700/50",
    heading: "text-amber-700 dark:text-amber-400",
  },
  gem_bearing: {
    label:   "Gem",
    text:    "text-ui-accent-readable dark:text-cyber-cyan",
    badge:   "bg-cyan-100 text-cyan-800 ring-1 ring-cyan-300 dark:bg-cyan-950 dark:text-cyber-cyan dark:ring-cyan-700/50",
    heading: "text-ui-accent-readable dark:text-cyber-cyan",
  },
};

function cat(c: MarketCommodity) {
  return CAT[c.category] ?? CAT.standard_metal;
}

const BAY_EXTRA: Record<
  "flora" | "fauna" | "unknown",
  { heading: string; title: string }
> = {
  flora: {
    title: "Flora & biomass",
    heading: "text-teal-700 dark:text-teal-400",
  },
  fauna: {
    title: "Fauna & organics",
    heading: "text-violet-700 dark:text-violet-400",
  },
  unknown: {
    title: "Unmapped bay",
    heading: "text-zinc-500 dark:text-zinc-400",
  },
};

/** Section keys: market metals (board categories), then flora / fauna / unmapped keys. */
export const BAY_TILE_CATEGORY_ORDER = [
  "standard_metal",
  "exotic_metal",
  "gem_bearing",
  "flora",
  "fauna",
  "unknown",
] as const;
export type BayTileCategory = (typeof BAY_TILE_CATEGORY_ORDER)[number];

export function bayTileSectionTitle(section: BayTileCategory): string {
  switch (section) {
    case "standard_metal":
      return "Standard Metals";
    case "exotic_metal":
      return "Exotic & Strategic Metals";
    case "gem_bearing":
      return "Gem-Bearing Materials";
    case "flora":
      return BAY_EXTRA.flora.title;
    case "fauna":
      return BAY_EXTRA.fauna.title;
    case "unknown":
      return BAY_EXTRA.unknown.title;
  }
}

export function bayTileSectionHeadingClass(section: BayTileCategory): string {
  if (section === "flora" || section === "fauna" || section === "unknown") {
    return `font-mono text-[11px] font-semibold uppercase tracking-widest ${BAY_EXTRA[section].heading}`;
  }
  return `font-mono text-[11px] font-semibold uppercase tracking-widest ${CAT[section].heading}`;
}

/** Card shell aligned with Commodity Board category colors (left rail + subtle fill + ring). */
export function bayTileCardClass(section: BayTileCategory): string {
  const base =
    "min-w-0 w-full max-w-full rounded-md px-2 py-1.5 shadow-sm ring-1 transition-colors hover:bg-zinc-950/40";
  switch (section) {
    case "standard_metal":
      return `${base} border-l-[3px] border-l-emerald-500/75 bg-gradient-to-br from-emerald-950/35 to-zinc-950/90 ring-emerald-900/35`;
    case "exotic_metal":
      return `${base} border-l-[3px] border-l-amber-500/75 bg-gradient-to-br from-amber-950/30 to-zinc-950/90 ring-amber-900/35`;
    case "gem_bearing":
      return `${base} border-l-[3px] border-l-cyan-500/70 bg-gradient-to-br from-cyan-950/35 to-zinc-950/90 ring-cyan-800/40`;
    case "flora":
      return `${base} border-l-[3px] border-l-teal-500/75 bg-gradient-to-br from-teal-950/35 to-zinc-950/90 ring-teal-900/35`;
    case "fauna":
      return `${base} border-l-[3px] border-l-violet-500/75 bg-gradient-to-br from-violet-950/35 to-zinc-950/90 ring-violet-900/35`;
    case "unknown":
      return `${base} border-l-[3px] border-l-zinc-600 bg-zinc-900/70 ring-zinc-800/50`;
  }
}

export function commodityStyle(c: MarketCommodity) {
  return cat(c);
}

// ─── Price delta helper ───────────────────────────────────────────────────────

export function priceDelta(sell: number, base: number) {
  if (!base) return { icon: "—", pct: 0, cls: "text-ui-muted" };
  const pct = Math.round(((sell - base) / base) * 100);
  if (pct > 0) return { icon: "▲", pct, cls: "text-emerald-600 dark:text-emerald-400" };
  if (pct < 0) return { icon: "▼", pct: Math.abs(pct), cls: "text-red-600 dark:text-red-400" };
  return { icon: "—", pct: 0, cls: "text-ui-muted" };
}

// ─── Shared hook ─────────────────────────────────────────────────────────────

function useMarket() {
  const loader = useCallback(() => getMarketState(), []);
  const resource = useUiResource(loader);
  const { reload } = resource;

  useEffect(() => {
    const id = setInterval(() => {
      if (!isUiPollPaused()) reload();
    }, UI_REFRESH_MS.marketSnapshot);
    return () => clearInterval(id);
  }, [reload]);

  return resource;
}

// ─── Single commodity row ─────────────────────────────────────────────────────

function CommodityRow({ c }: { c: MarketCommodity }) {
  const d = priceDelta(c.sellPriceCrPerTon, c.basePriceCrPerTon);
  const s = cat(c);
  return (
    <tr className="border-b border-cyan-900/40 transition-colors hover:bg-cyan-950/30">
      <td className="py-1.5 pr-3">
        <span className={`font-mono text-sm font-semibold ${s.text}`}>{c.name}</span>
      </td>
      <td className="py-1.5 pr-3">
        <span className={`rounded px-1.5 py-0.5 font-mono text-xs font-medium ${s.badge}`}>
          {s.label}
        </span>
      </td>
      <td className="py-1.5 pr-3 text-right font-mono text-sm text-ui-muted">
        {c.basePriceCrPerTon.toLocaleString()}
      </td>
      <td className="py-1.5 pr-3 text-right font-mono text-sm font-semibold text-foreground">
        {c.sellPriceCrPerTon.toLocaleString()}
      </td>
      <td className="py-1.5 pr-3 text-right font-mono text-sm text-ui-muted">
        {c.buyPriceCrPerTon.toLocaleString()}
      </td>
      <td className={`py-1.5 pl-3 text-right font-mono text-sm font-bold tabular-nums ${d.cls}`}>
        {d.icon} {d.pct > 0 ? `${d.pct}%` : "—"}
      </td>
    </tr>
  );
}

function SectionRow({ label, className }: { label: string; className: string }) {
  return (
    <tr>
      <td colSpan={6} className="pb-1 pt-3">
        <span className={`font-mono text-xs uppercase tracking-widest ${className}`}>
          — {label} —
        </span>
      </td>
    </tr>
  );
}

// ─── Full table (bottom of page) ─────────────────────────────────────────────

export function CommodityTickerTable() {
  const { data, loading, error, reload } = useMarket();
  const lastUpdated = useMemo(() => (data != null ? new Date() : null), [data]);

  const groups = data
    ? {
        standard_metal: data.commodities.filter((c) => c.category === "standard_metal"),
        exotic_metal:   data.commodities.filter((c) => c.category === "exotic_metal"),
        gem_bearing:    data.commodities.filter((c) => c.category === "gem_bearing"),
      }
    : null;

  return (
    <section className="overflow-hidden rounded border border-cyan-900/40 bg-zinc-950/80">
      {/* Header */}
      <div className="flex min-w-0 flex-col gap-2 border-b border-cyan-900/50 bg-cyan-950/40 px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="min-w-0 truncate font-mono text-xs font-semibold uppercase tracking-widest text-cyber-cyan">
          Market Rates — All Commodities
        </h2>
        <div className="flex shrink-0 items-center gap-2">
          {lastUpdated && (
            <span className="font-mono text-xs text-ui-muted">
              SYNC {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button
            type="button"
            onClick={reload}
            disabled={loading}
            className="rounded border border-cyan-700/50 px-1.5 py-0.5 font-mono text-xs text-cyber-cyan transition hover:border-cyan-500 hover:text-cyber-cyan disabled:opacity-30"
          >
            {loading ? "…" : "↻"}
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto px-3 pb-4 pt-1.5">
        {error && (
          <p className="py-1.5 font-mono text-sm text-red-600 dark:text-red-400">
            Market feed unavailable: {error}
          </p>
        )}
        {loading && !data && (
          <p className="animate-pulse py-3 text-center font-mono text-sm text-ui-muted">
            SYNCING MARKET FEED…
          </p>
        )}
        {groups && (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-cyan-900/50">
                {(
                  [
                    ["Commodity", "text-left",  "pr-3"],
                    ["Type",      "text-left",  "pr-3"],
                    ["Base cr/t", "text-right", "pr-3"],
                    ["Sell cr/t", "text-right", "pr-3"],
                    ["Buy cr/t",  "text-right", ""],
                    ["Δ Market",  "text-right", "pl-3"],
                  ] as [string, string, string][]
                ).map(([h, align, extra]) => (
                  <th
                    key={h}
                    className={`pb-1.5 font-mono text-xs uppercase tracking-wider text-ui-muted ${align} ${extra}`}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <SectionRow label="Standard Metals"           className={CAT.standard_metal.heading} />
              {groups.standard_metal.map((c) => <CommodityRow key={c.key} c={c} />)}

              <SectionRow label="Exotic & Strategic Metals" className={CAT.exotic_metal.heading} />
              {groups.exotic_metal.map((c) => <CommodityRow key={c.key} c={c} />)}

              <SectionRow label="Gem-Bearing Materials"     className={CAT.gem_bearing.heading} />
              {groups.gem_bearing.map((c) => <CommodityRow key={c.key} c={c} />)}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
