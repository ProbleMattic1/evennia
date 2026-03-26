"use client";

import { useCallback, useEffect, useState } from "react";

import {
  buyListedPropertyDeed,
  getPropertyDeedListings,
  listPropertyDeedForSale,
  type PropertyDeedListingRow,
} from "@/lib/ui-api";
import {
  exchangePanelEmptyClass,
  exchangePanelOuterClass,
  exchangePanelToolbarClass,
  exchangePanelToolbarTitleClass,
} from "@/lib/exchange-panel-classes";

type PropertyDeedMarketPanelProps = {
  /** When shown on a property claim page, prefill the list form with this deed id. */
  defaultClaimId?: number;
};

export function PropertyDeedMarketPanel({ defaultClaimId }: PropertyDeedMarketPanelProps) {
  const [listings, setListings] = useState<PropertyDeedListingRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ ok: boolean; message: string } | null>(null);
  const [buyingId, setBuyingId] = useState<number | null>(null);
  const [listClaimId, setListClaimId] = useState("");
  const [listPrice, setListPrice] = useState("");
  const [listBusy, setListBusy] = useState(false);

  useEffect(() => {
    if (defaultClaimId != null && Number.isFinite(defaultClaimId) && defaultClaimId > 0) {
      setListClaimId(String(Math.floor(defaultClaimId)));
    }
  }, [defaultClaimId]);

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
    setFeedback(null);
    try {
      await buyListedPropertyDeed({ claimId: row.claimId });
      setFeedback({ ok: true, message: `Purchased ${row.key}.` });
      await reload();
    } catch (e) {
      setFeedback({
        ok: false,
        message: e instanceof Error ? e.message : "Purchase failed.",
      });
    } finally {
      setBuyingId(null);
    }
  }

  async function handleList() {
    const cid = Number(listClaimId);
    const price = Number(listPrice);
    if (!Number.isFinite(cid) || cid <= 0) {
      setFeedback({ ok: false, message: "Enter a valid deed object id (claim id)." });
      return;
    }
    if (!Number.isFinite(price) || price < 0) {
      setFeedback({ ok: false, message: "Enter a valid price (credits)." });
      return;
    }
    setListBusy(true);
    setFeedback(null);
    try {
      await listPropertyDeedForSale({ claimId: cid, price: Math.floor(price) });
      setFeedback({ ok: true, message: "Deed listed." });
      setListClaimId("");
      setListPrice("");
      await reload();
    } catch (e) {
      setFeedback({
        ok: false,
        message: e instanceof Error ? e.message : "Listing failed.",
      });
    } finally {
      setListBusy(false);
    }
  }

  return (
    <div className={exchangePanelOuterClass}>
      <div className={exchangePanelToolbarClass}>
        <h2 className={exchangePanelToolbarTitleClass}>Player deed resale</h2>
      </div>

      <p className="mt-2 px-2 text-[11px] text-zinc-500 dark:text-cyan-500/70">
        Deeds you list are held in hub escrow (same pattern as mining package listings). Claim id is the
        deed object id (Deed section at the top of this page). In-game:{" "}
        <span className="font-mono">listpropertydeed</span> /{" "}
        <span className="font-mono">buypropertydeed</span>.
      </p>

      {feedback && (
        <p
          className={`mx-2 mt-2 rounded px-2 py-1.5 text-xs ${
            feedback.ok
              ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-900/25 dark:text-emerald-400"
              : "bg-red-50 text-red-700 dark:bg-red-900/25 dark:text-red-400"
          }`}
        >
          {feedback.message}
        </p>
      )}

      <div className="mt-3 border-t border-zinc-200 px-2 py-2 dark:border-cyan-900/40">
        <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500 dark:text-cyan-500/80">
          List your deed
        </p>
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-0.5 text-[11px] text-zinc-600 dark:text-zinc-400">
            Claim id
            <input
              type="text"
              inputMode="numeric"
              value={listClaimId}
              onChange={(ev) => setListClaimId(ev.target.value)}
              className="w-28 rounded border border-zinc-300 bg-white px-2 py-1 font-mono text-sm dark:border-cyan-800 dark:bg-zinc-900 dark:text-zinc-200"
              placeholder="#id"
            />
          </label>
          <label className="flex flex-col gap-0.5 text-[11px] text-zinc-600 dark:text-zinc-400">
            Price (cr)
            <input
              type="text"
              inputMode="numeric"
              value={listPrice}
              onChange={(ev) => setListPrice(ev.target.value)}
              className="w-32 rounded border border-zinc-300 bg-white px-2 py-1 font-mono text-sm dark:border-cyan-800 dark:bg-zinc-900 dark:text-zinc-200"
            />
          </label>
          <button
            type="button"
            disabled={listBusy}
            onClick={() => void handleList()}
            className="rounded bg-zinc-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-zinc-700 disabled:opacity-50 dark:bg-cyan-800 dark:hover:bg-cyan-700"
          >
            {listBusy ? "…" : "List deed"}
          </button>
        </div>
      </div>

      <div className="mt-2 border-t border-zinc-200 px-2 py-2 dark:border-cyan-900/40">
        <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500 dark:text-cyan-500/80">
          Listed deeds
        </p>
        {loading ? (
          <p className="mt-2 text-sm text-zinc-500">Loading…</p>
        ) : error ? (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>
        ) : listings.length === 0 ? (
          <p className={`mt-2 ${exchangePanelEmptyClass}`}>No deeds listed.</p>
        ) : (
          <ul className="mt-2 flex flex-col gap-2">
            {listings.map((row) => (
              <li
                key={row.claimId}
                className="flex flex-wrap items-center justify-between gap-2 rounded border border-zinc-200 px-2 py-2 dark:border-cyan-900/40"
              >
                <div className="min-w-0">
                  <div className="truncate font-mono text-sm text-zinc-900 dark:text-zinc-100">
                    {row.key}
                  </div>
                  <div className="text-[11px] text-zinc-500 dark:text-cyan-500/70">
                    #{row.claimId} · {row.kind} · {row.lotKey || "—"} · seller {row.sellerKey}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="font-mono text-sm tabular-nums text-amber-700 dark:text-amber-400">
                    {row.price.toLocaleString()} cr
                  </span>
                  <button
                    type="button"
                    disabled={buyingId === row.claimId}
                    onClick={() => void handleBuy(row)}
                    className="rounded bg-cyan-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-50 dark:bg-cyan-700"
                  >
                    {buyingId === row.claimId ? "…" : "Buy"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
