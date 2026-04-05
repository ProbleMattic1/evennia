"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";

import { PanelExpandButton } from "@/components/panel-expand-button";
import type { CsInventory } from "@/lib/control-surface-api";
import { formatCr as cr } from "@/lib/format-units";
import {
  getPackageListingsState,
  packageListForSale,
  postPackageBuyListed,
  type PackageListingRow,
} from "@/lib/ui-api";
import { useDashboardPanelOpen } from "@/lib/use-dashboard-panel-open";
import {
  DASHBOARD_PANEL_BODY,
  DASHBOARD_PANEL_HEADER,
  DASHBOARD_PANEL_SECTION,
  DASHBOARD_PANEL_TITLE,
} from "@/lib/dashboard-panel-chrome";

function Panel({
  panelKey,
  title,
  headerActions,
  children,
}: {
  panelKey: string;
  title: string;
  headerActions?: ReactNode;
  children: ReactNode;
}) {
  const [open, setOpen] = useDashboardPanelOpen(panelKey, true);
  return (
    <section className={DASHBOARD_PANEL_SECTION}>
      <div className={DASHBOARD_PANEL_HEADER}>
        <span className={DASHBOARD_PANEL_TITLE}>{title}</span>
        <div className="ml-auto flex shrink-0 items-center gap-1 normal-case tracking-normal">
          {headerActions}
          <PanelExpandButton
            open={open}
            onClick={() => setOpen((v) => !v)}
            aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          />
        </div>
      </div>
      {open ? <div className={DASHBOARD_PANEL_BODY}>{children}</div> : null}
    </section>
  );
}

function TinyButton({
  onClick,
  disabled,
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="shrink-0 rounded border border-cyan-800/60 px-1 py-0 text-xs text-cyber-cyan hover:bg-cyan-900/40 disabled:opacity-40"
    >
      {children}
    </button>
  );
}

function flatMiningPackages(inv: CsInventory): { id: number; key: string; estimatedValue?: number }[] {
  const rows = inv.byBucket["mining_package"] ?? [];
  return rows.flatMap((item) => {
    const ids = item.stacked && item.ids?.length ? item.ids : [item.id];
    return ids.map((id) => ({
      id,
      key: item.key,
      estimatedValue: item.estimatedValue,
    }));
  });
}

const LIST_SCROLL_CLASS =
  "max-h-[min(160px,28vh)] min-h-[32px] overflow-y-auto overflow-x-hidden pr-0.5 [scrollbar-gutter:stable]";

export function PackageMarketPanel({
  inventory,
  run,
  busy,
}: {
  inventory: CsInventory;
  run: (fn: () => Promise<unknown>) => void;
  busy: boolean;
}) {
  const [listings, setListings] = useState<PackageListingRow[]>([]);
  const [listErr, setListErr] = useState<string | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [prices, setPrices] = useState<Record<number, string>>({});

  const loadListings = useCallback(() => {
    setListLoading(true);
    setListErr(null);
    getPackageListingsState()
      .then((s) => {
        setListings(s.listings ?? []);
      })
      .catch((e: unknown) => {
        setListErr(e instanceof Error ? e.message : "Failed to load listings");
        setListings([]);
      })
      .finally(() => setListLoading(false));
  }, []);

  useEffect(() => {
    loadListings();
  }, [loadListings]);

  const pkgs = flatMiningPackages(inventory);

  return (
    <Panel
      panelKey="package-market"
      title="Package market"
      headerActions={
        <TinyButton onClick={() => loadListings()} disabled={busy || listLoading}>
          Refresh
        </TinyButton>
      }
    >
      <p className="mb-1 text-ui-caption text-ui-muted">
        List mining packages for credits, or buy packages other players listed.
      </p>
      {listErr ? <p className="mb-1 text-red-400">{listErr}</p> : null}
      <div className="mb-2">
        <div className="mb-0.5 text-[10px] font-bold uppercase tracking-wide text-ui-muted">Listed for sale</div>
        {listLoading ? (
          <p className="text-ui-muted">Loading…</p>
        ) : listings.length === 0 ? (
          <p className="text-ui-muted">No packages listed.</p>
        ) : (
          <div className={LIST_SCROLL_CLASS}>
            {listings.map((row) => (
              <div
                key={`${row.packageId}-${row.sellerKey}-${row.price}`}
                className="mb-1 flex flex-wrap items-baseline gap-1 border-b border-zinc-800/80 pb-1 last:mb-0 last:border-0"
              >
                <span className="min-w-0 flex-1 truncate font-mono text-foreground">{row.key}</span>
                <span className="font-mono text-ui-muted">{cr(row.price)}</span>
                <span className="text-ui-caption text-ui-muted">from {row.sellerKey}</span>
                {row.estimatedValue != null ? (
                  <span className="text-ui-caption text-ui-muted">est. {cr(row.estimatedValue)}</span>
                ) : null}
                <TinyButton
                  disabled={busy}
                  onClick={() =>
                    run(async () => {
                      await postPackageBuyListed({ packageId: row.packageId });
                      loadListings();
                    })
                  }
                >
                  Buy
                </TinyButton>
              </div>
            ))}
          </div>
        )}
      </div>
      {pkgs.length > 0 ? (
        <div>
          <div className="mb-0.5 text-[10px] font-bold uppercase tracking-wide text-ui-muted">List from inventory</div>
          <div className={LIST_SCROLL_CLASS}>
            {pkgs.map((p) => (
              <div
                key={p.id}
                className="mb-1 flex flex-wrap items-center gap-1 border-b border-zinc-800/80 pb-1 last:mb-0 last:border-0"
              >
                <span className="min-w-0 flex-1 truncate font-mono text-foreground">
                  {p.key} #{p.id}
                </span>
                {p.estimatedValue != null ? (
                  <span className="text-ui-caption text-ui-muted">est. {cr(p.estimatedValue)}</span>
                ) : null}
                <input
                  type="number"
                  min={1}
                  step={1}
                  placeholder="cr"
                  className="w-20 rounded border border-cyan-900/50 bg-zinc-900 px-1 py-0.5 font-mono text-xs text-foreground"
                  value={prices[p.id] ?? ""}
                  onChange={(e) => setPrices((prev) => ({ ...prev, [p.id]: e.target.value }))}
                />
                <TinyButton
                  disabled={busy}
                  onClick={() => {
                    const raw = prices[p.id]?.trim() ?? "";
                    const n = Number(raw);
                    if (!Number.isFinite(n) || n < 1) return;
                    run(async () => {
                      await packageListForSale({ packageId: p.id, price: Math.floor(n) });
                      setPrices((prev) => {
                        const next = { ...prev };
                        delete next[p.id];
                        return next;
                      });
                      loadListings();
                    });
                  }}
                >
                  List
                </TinyButton>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="text-ui-muted">No mining packages in inventory to list.</p>
      )}
    </Panel>
  );
}
