"use client";

import { useCallback, useEffect, useState } from "react";

import {
  buyListedPropertyDeed,
  getPropertyDeedListings,
  type PropertyDeedListingRow,
} from "@/lib/ui-api";
import { exchangePanelEmptyClass, panelPrimaryButtonClass } from "@/lib/exchange-panel-classes";

type PropertyDeedResaleBrowseProps = {
  onPurchased?: () => void;
};

export function PropertyDeedResaleBrowse({ onPurchased }: PropertyDeedResaleBrowseProps) {
  const [listings, setListings] = useState<PropertyDeedListingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [purchaseError, setPurchaseError] = useState<string | null>(null);
  const [purchaseSuccess, setPurchaseSuccess] = useState<string | null>(null);
  const [buyingId, setBuyingId] = useState<number | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getPropertyDeedListings();
      setListings(res.listings ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load deed listings.");
      setListings([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function handleBuy(row: PropertyDeedListingRow) {
    setBuyingId(row.claimId);
    setPurchaseError(null);
    setPurchaseSuccess(null);
    try {
      const res = await buyListedPropertyDeed({ claimId: row.claimId });
      setPurchaseSuccess(res.message ?? `Purchased ${row.key}.`);
      onPurchased?.();
      await reload();
    } catch (e) {
      setPurchaseError(e instanceof Error ? e.message : "Purchase failed.");
    } finally {
      setBuyingId(null);
    }
  }

  return (
    <div
      id="property-deed-resale-market"
      className="scroll-mt-4 mt-3 border-t border-cyan-900/40 pt-3"
    >
      <p className="text-xs font-medium uppercase tracking-wide text-ui-muted">Listed deeds</p>
      {purchaseSuccess ? (
        <p className="mt-2 text-xs text-emerald-400">{purchaseSuccess}</p>
      ) : null}
      {purchaseError ? <p className="mt-2 text-xs text-red-400">{purchaseError}</p> : null}
      {loading ? (
        <p className="mt-2 text-sm text-ui-muted">Loading…</p>
      ) : error ? (
        <p className="mt-2 text-sm text-red-400">{error}</p>
      ) : listings.length === 0 ? (
        <p className={`mt-2 ${exchangePanelEmptyClass}`}>No deeds listed.</p>
      ) : (
        <ul className="mt-2 flex flex-col gap-2">
          {listings.map((row) => (
            <li
              key={row.claimId}
              className="flex flex-wrap items-center justify-between gap-2 rounded border border-cyan-900/40 bg-zinc-950/60 px-2 py-2"
            >
              <div className="min-w-0">
                <div className="truncate font-mono text-sm text-foreground">{row.key}</div>
                <div className="text-xs text-ui-muted">
                  #{row.claimId} · {row.kind} · {row.lotKey || "—"} · seller {row.sellerKey}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <span className="font-mono text-sm tabular-nums text-amber-400">
                  {row.price.toLocaleString()} cr
                </span>
                <button
                  type="button"
                  disabled={buyingId === row.claimId}
                  onClick={() => void handleBuy(row)}
                  className={panelPrimaryButtonClass}
                >
                  {buyingId === row.claimId ? "…" : "Buy"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
