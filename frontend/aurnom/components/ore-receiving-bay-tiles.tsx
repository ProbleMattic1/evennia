"use client";

import { useCallback, useEffect, useMemo } from "react";

import {
  BAY_TILE_CATEGORY_ORDER,
  bayTileCardClass,
  bayTileSectionHeadingClass,
  bayTileSectionTitle,
  commodityStyle,
  priceDelta,
} from "@/components/commodity-ticker";
import { PanelExpandButton } from "@/components/panel-expand-button";
import { formatCr as cr } from "@/lib/format-units";
import { useDashboardPanelOpen } from "@/lib/use-dashboard-panel-open";
import type { MarketCommodity, OreReceivingBayRow } from "@/lib/ui-api";
import { getMarketState } from "@/lib/ui-api";
import { isUiPollPaused, UI_REFRESH_MS } from "@/lib/ui-refresh-policy";
import { useUiResource } from "@/lib/use-ui-resource";

type BaySection = (typeof BAY_TILE_CATEGORY_ORDER)[number];

function BayResourceTile({
  r,
  section,
  commodity,
}: {
  r: OreReceivingBayRow;
  section: BaySection;
  commodity: MarketCommodity | undefined;
}) {
  const FEE = 0.03;
  const est = typeof r.estimatedValueCr === "number" && !Number.isNaN(r.estimatedValueCr) ? r.estimatedValueCr : null;
  const holdingCost = est == null ? null : Math.floor(est * (1 - FEE));
  const soldWorth = est == null ? null : Math.floor(est * (1 + FEE));
  const style = commodity ? commodityStyle(commodity) : null;
  const delta = commodity ? priceDelta(commodity.sellPriceCrPerTon, commodity.basePriceCrPerTon) : null;

  return (
    <div className={bayTileCardClass(section)} title={r.key}>
      <div className="flex items-baseline justify-between gap-2">
        <span
          className={`min-w-0 truncate text-xs font-semibold ${style?.text ?? "text-foreground"}`}
        >
          {r.displayName}
        </span>
        <div className="flex shrink-0 items-baseline gap-1.5">
          {delta ? (
            <span className={`font-mono text-[10px] font-bold tabular-nums ${delta.cls}`} title="Market vs base">
              {delta.icon} {delta.pct > 0 ? `${delta.pct}%` : "—"}
            </span>
          ) : null}
          <span className="font-mono tabular-nums text-xs text-cyan-200 dark:text-cyber-cyan">
            {r.tons.toLocaleString(undefined, { maximumFractionDigits: 2 })}t
          </span>
        </div>
      </div>
      <div className="mt-1 flex justify-end text-[10px] text-zinc-500 dark:text-zinc-400">
        <span
          className="font-mono tabular-nums text-zinc-700 dark:text-zinc-300"
          title="Estimated value at local bids (credits)"
        >
          {cr(est)}
        </span>
      </div>
      <div className="mt-1 grid min-w-0 grid-cols-2 gap-x-2 gap-y-0.5 border-t border-zinc-800/60 pt-1 text-[10px] dark:border-zinc-700/50">
        <span className="truncate text-zinc-500 dark:text-zinc-400">hold cost</span>
        <span className="text-right font-mono tabular-nums text-zinc-900 dark:text-zinc-100">
          {holdingCost == null ? "—" : cr(holdingCost)}
        </span>
        <span className="truncate text-zinc-500 dark:text-zinc-400">sold (+3%)</span>
        <span className="text-right font-mono tabular-nums text-zinc-900 dark:text-zinc-100">
          {soldWorth == null ? "—" : cr(soldWorth)}
        </span>
      </div>
    </div>
  );
}

function BayTileSection({
  sectionKey,
  sectionRows,
  keyToCommodity,
}: {
  sectionKey: BaySection;
  sectionRows: OreReceivingBayRow[];
  keyToCommodity: Map<string, MarketCommodity>;
}) {
  const [open, setOpen] = useDashboardPanelOpen(`processing:ore-bay:${sectionKey}`, true);
  const headingLabel = bayTileSectionTitle(sectionKey);

  return (
    <div>
      <div className="mb-2 flex min-w-0 items-center gap-1 border-b border-cyan-900/30 pb-1 dark:border-cyan-800/30">
        <span className={`min-w-0 flex-1 truncate ${bayTileSectionHeadingClass(sectionKey)}`}>
          — {headingLabel} —
        </span>
        <PanelExpandButton
          open={open}
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${headingLabel}`}
          className="shrink-0"
        />
      </div>
      {open ? (
        <div className="flex min-w-0 flex-wrap gap-2">
          {sectionRows.map((r) => (
            <BayResourceTile key={r.key} r={r} section={sectionKey} commodity={keyToCommodity.get(r.key)} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

/**
 * Ore receiving bay tiles grouped by market category (same sections as Commodity Board).
 */
export function OreReceivingBayTiles({ rows }: { rows: OreReceivingBayRow[] }) {
  const marketLoader = useCallback(() => getMarketState(), []);
  const { data: marketData, reload: reloadMarket } = useUiResource(marketLoader);

  useEffect(() => {
    const id = window.setInterval(() => {
      if (!isUiPollPaused()) reloadMarket();
    }, UI_REFRESH_MS.marketSnapshot);
    return () => window.clearInterval(id);
  }, [reloadMarket]);

  const keyToCommodity = useMemo(() => {
    const m = new Map<string, MarketCommodity>();
    for (const c of marketData?.commodities ?? []) {
      m.set(c.key, c);
    }
    return m;
  }, [marketData]);

  const sections = useMemo(() => {
    const by: Record<BaySection, OreReceivingBayRow[]> = {
      standard_metal: [],
      exotic_metal: [],
      gem_bearing: [],
      flora: [],
      fauna: [],
      unknown: [],
    };
    for (const r of rows) {
      const pipeline = r.rawPipeline ?? "unknown";
      if (pipeline === "flora") {
        by.flora.push(r);
        continue;
      }
      if (pipeline === "fauna") {
        by.fauna.push(r);
        continue;
      }
      if (pipeline === "unknown") {
        by.unknown.push(r);
        continue;
      }
      // mining: bucket by market commodity category; keys missing from board → unmapped
      const c = keyToCommodity.get(r.key);
      const cat = c?.category;
      if (cat === "standard_metal" || cat === "exotic_metal" || cat === "gem_bearing") {
        by[cat].push(r);
      } else {
        by.unknown.push(r);
      }
    }
    for (const k of BAY_TILE_CATEGORY_ORDER) {
      by[k].sort((a, b) => a.displayName.localeCompare(b.displayName));
    }
    return BAY_TILE_CATEGORY_ORDER.map((key) => ({ key, rows: by[key] })).filter((s) => s.rows.length > 0);
  }, [rows, keyToCommodity]);

  if (!rows.length) return null;

  return (
    <div className="mt-2 space-y-3">
      {sections.map(({ key: sectionKey, rows: sectionRows }) => (
        <BayTileSection
          key={sectionKey}
          sectionKey={sectionKey}
          sectionRows={sectionRows}
          keyToCommodity={keyToCommodity}
        />
      ))}
    </div>
  );
}
