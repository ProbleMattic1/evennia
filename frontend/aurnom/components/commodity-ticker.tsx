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

// ─── Price delta helper ───────────────────────────────────────────────────────

function priceDelta(sell: number, base: number) {
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

// ─── Scrolling strip (top of page) ───────────────────────────────────────────

export function CommodityTickerStrip() {
  const { data, loading } = useMarket();

  if (loading && !data) {
    return (
      <div className="overflow-hidden rounded border border-cyan-900/40 bg-zinc-950/80 px-3 py-2">
        <p className="animate-pulse font-mono text-sm text-ui-muted">
          SYNCING MARKET FEED…
        </p>
      </div>
    );
  }

  if (!data) return null;

  const items = [...data.commodities, ...data.commodities]; // duplicate for seamless loop

  return (
    <div className="overflow-hidden rounded border border-cyan-900/40 bg-zinc-950/80">
      {/* Header row */}
      <div className="flex min-w-0 items-center justify-between border-b border-cyan-900/50 bg-cyan-950/40 px-3 py-1.5">
        <div className="flex min-w-0 items-center gap-2">
          <span className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-emerald-500 dark:bg-cyan-400" />
          <span className="min-w-0 truncate font-mono text-xs font-semibold uppercase tracking-widest text-cyber-cyan">
            Aurnom Commodity Exchange · Live Pricing
          </span>
        </div>
      </div>

      {/* Scrolling strip */}
      <div className="overflow-hidden py-1.5">
        <div
          className="flex w-max gap-10 whitespace-nowrap px-3"
          style={{ animation: "ace-ticker 50s linear infinite" }}
        >
          {items.map((c, i) => {
            const d = priceDelta(c.sellPriceCrPerTon, c.basePriceCrPerTon);
            return (
              <span
                key={`${c.key}-${i}`}
                className="inline-flex items-center gap-1.5 font-mono text-sm"
              >
                <span className={cat(c).text}>{c.name.toUpperCase()}</span>
                <span className="text-ui-muted dark:text-foreground">
                  {c.sellPriceCrPerTon.toLocaleString()}cr/t
                </span>
                <span className={d.cls}>
                  {d.icon}
                  {d.pct > 0 ? ` ${d.pct}%` : ""}
                </span>
              </span>
            );
          })}
        </div>
      </div>

      <style>{`
        @keyframes ace-ticker {
          from { transform: translateX(0); }
          to   { transform: translateX(-50%); }
        }
      `}</style>
    </div>
  );
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
