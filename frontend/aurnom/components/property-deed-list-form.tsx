"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { listPropertyDeedForSale } from "@/lib/ui-api";

type PropertyDeedListFormProps = {
  /** When on a property claim page, prefill the list form with this deed id. */
  defaultClaimId?: number;
};

export function PropertyDeedListForm({ defaultClaimId }: PropertyDeedListFormProps) {
  const router = useRouter();
  const [listClaimId, setListClaimId] = useState("");
  const [listPrice, setListPrice] = useState("");
  const [listBusy, setListBusy] = useState(false);
  const [listMsg, setListMsg] = useState<string | null>(null);

  useEffect(() => {
    if (defaultClaimId != null && Number.isFinite(defaultClaimId) && defaultClaimId > 0) {
      setListClaimId(String(Math.floor(defaultClaimId)));
    }
  }, [defaultClaimId]);

  const handleList = useCallback(async () => {
    const cid = Number(listClaimId);
    const price = Number(listPrice);
    if (!Number.isFinite(cid) || cid <= 0) {
      setListMsg("Enter a valid deed object id (claim id).");
      return;
    }
    if (!Number.isFinite(price) || price < 0) {
      setListMsg("Enter a valid price (credits).");
      return;
    }
    setListBusy(true);
    setListMsg(null);
    try {
      const res = await listPropertyDeedForSale({ claimId: cid, price: Math.floor(price) });
      setListMsg(res.message ?? "Listed.");
      router.push("/real-estate#property-deed-resale-market");
      router.refresh();
    } catch (e) {
      setListMsg(e instanceof Error ? e.message : "Listing failed.");
    } finally {
      setListBusy(false);
    }
  }, [listClaimId, listPrice, router]);

  return (
    <>
      <p className="mt-1 text-[12px] text-zinc-500 dark:text-cyan-500/70">
        List this deed on the property market at your price (hub escrow until sold). Buyers browse listed
        deeds on the{" "}
        <Link href="/real-estate#property-deed-resale-market" className="text-sky-700 underline dark:text-sky-400">
          Real Estate office
        </Link>
        . In-game: <span className="font-mono">listpropertydeed</span> /{" "}
        <span className="font-mono">buypropertydeed</span>.
      </p>
      {listMsg ? (
        <p className="mt-2 font-mono text-[12px] text-zinc-500 dark:text-zinc-400">{listMsg}</p>
      ) : null}
      <div className="mt-3 border-t border-cyan-900/40 pt-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">List your deed</p>
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-0.5 text-[11px] text-zinc-500">
            Claim id
            <input
              type="text"
              inputMode="numeric"
              value={listClaimId}
              onChange={(ev) => setListClaimId(ev.target.value)}
              className="w-28 rounded border border-cyan-800/60 bg-zinc-900 px-2 py-1 font-mono text-sm text-zinc-200 dark:bg-zinc-950"
              placeholder="#id"
            />
          </label>
          <label className="flex flex-col gap-0.5 text-[11px] text-zinc-500">
            Price (cr)
            <input
              type="text"
              inputMode="numeric"
              value={listPrice}
              onChange={(ev) => setListPrice(ev.target.value)}
              className="w-32 rounded border border-cyan-800/60 bg-zinc-900 px-2 py-1 font-mono text-sm text-zinc-200 dark:bg-zinc-950"
            />
          </label>
          <button
            type="button"
            disabled={listBusy}
            onClick={() => void handleList()}
            className="rounded border border-cyan-800/60 bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/40 disabled:opacity-50 dark:bg-cyan-950/50"
          >
            {listBusy ? "…" : "List deed"}
          </button>
        </div>
      </div>
    </>
  );
}
