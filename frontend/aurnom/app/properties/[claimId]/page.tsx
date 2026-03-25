"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { getPropertyClaimDetail, type PropertyClaimDetailState } from "@/lib/ui-api";

const KIND_LABEL: Record<string, string> = {
  residential: "Residential",
  commercial: "Commercial",
  industrial: "Industrial",
};

export default function PropertyClaimDetailPage() {
  const params = useParams();
  const raw = params.claimId;
  const claimId = Number(Array.isArray(raw) ? raw[0] : raw);

  const [data, setData] = useState<PropertyClaimDetailState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!Number.isFinite(claimId)) {
      setError("Invalid property claim.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await getPropertyClaimDetail(claimId);
      if (!res.ok) {
        setError(res.message ?? "Unable to load property claim.");
        setData(null);
      } else {
        setData(res);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load property claim.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [claimId]);

  useEffect(() => {
    void load();
  }, [load]);

  const claim = data?.claim;
  const lot = data?.lot;

  return (
    <main className="main-content">
      <header className="page-header flex flex-wrap items-start justify-between gap-2 border-b border-zinc-200 py-3 pl-2 dark:border-cyan-900/50">
        <div className="px-2">
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
            {claim?.key ?? "Property claim"}
          </h1>
          <p className="mt-0.5 text-[12px] text-zinc-500 dark:text-zinc-400">
            {claim?.description ?? "Property deed"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 px-2">
          <Link
            href="/real-estate"
            className="rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-800 hover:bg-zinc-100 dark:border-cyan-700/50 dark:text-cyan-400 dark:hover:bg-cyan-950/40"
          >
            Real Estate Office
          </Link>
          <Link
            href="/"
            className="rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-800 hover:bg-zinc-100 dark:border-cyan-700/50 dark:text-cyan-400 dark:hover:bg-cyan-950/40"
          >
            Home
          </Link>
        </div>
      </header>

      {loading && <p className="px-2 py-3 font-mono text-sm text-zinc-500">Loading…</p>}
      {error && <p className="px-2 py-3 font-mono text-sm text-red-600 dark:text-red-400">{error}</p>}

      {data?.ok && claim && (
        <div className="mt-4 space-y-3 px-2">
          <section className="rounded border border-zinc-200 bg-zinc-50 p-3 dark:border-cyan-900/50 dark:bg-zinc-950/80">
            <h2 className="section-label">Deed</h2>
            <dl className="mt-2 grid gap-1 text-sm">
              <div className="flex justify-between gap-2">
                <dt className="text-zinc-500">Kind</dt>
                <dd className="font-mono text-zinc-800 dark:text-zinc-200">
                  {KIND_LABEL[claim.kind] ?? claim.kind}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-zinc-500">Parcel</dt>
                <dd className="font-mono text-zinc-800 dark:text-zinc-200">{claim.lotKey || "—"}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-zinc-500">Tier (on deed)</dt>
                <dd className="font-mono text-zinc-800 dark:text-zinc-200">{claim.lotTier}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-zinc-500">Object ID</dt>
                <dd className="font-mono text-zinc-800 dark:text-zinc-200">#{claim.id}</dd>
              </div>
            </dl>
          </section>

          {lot ? (
            <section className="rounded border border-zinc-200 bg-white p-3 dark:border-cyan-900/50 dark:bg-zinc-900/40">
              <h2 className="section-label">Parcel</h2>
              <dl className="mt-2 grid gap-1 text-sm">
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">Lot</dt>
                  <dd className="font-mono text-zinc-800 dark:text-zinc-200">{lot.lotKey}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">Zone</dt>
                  <dd className="text-zinc-800 dark:text-zinc-200">{lot.zoneLabel}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">Tier</dt>
                  <dd className="font-mono text-zinc-800 dark:text-zinc-200">
                    {lot.tierLabel} ({lot.tier})
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">Size (units)</dt>
                  <dd className="font-mono text-zinc-800 dark:text-zinc-200">{lot.sizeUnits}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">Claimed</dt>
                  <dd className="font-mono text-zinc-800 dark:text-zinc-200">
                    {lot.isClaimed ? "Yes" : "No"}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">Recorded owner</dt>
                  <dd className="font-mono text-right text-[12px] text-zinc-800 dark:text-zinc-200">
                    {lot.ownerKey ?? "—"}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">Sovereign list price (reference)</dt>
                  <dd className="font-mono tabular-nums text-zinc-800 dark:text-zinc-200">
                    {lot.referenceListPriceCr.toLocaleString()} cr
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">On primary market</dt>
                  <dd className="font-mono text-zinc-800 dark:text-zinc-200">
                    {lot.purchasable ? "Yes" : "No"}
                  </dd>
                </div>
                {lot.roomKey && (
                  <div className="flex justify-between gap-2">
                    <dt className="text-zinc-500">Room</dt>
                    <dd className="font-mono text-right text-[12px] text-zinc-800 dark:text-zinc-200">
                      {lot.roomKey}
                    </dd>
                  </div>
                )}
              </dl>
              {lot.description && (
                <p className="mt-3 border-t border-zinc-100 pt-3 text-[12px] text-zinc-600 dark:border-cyan-900/40 dark:text-cyan-500/80">
                  {lot.description}
                </p>
              )}
              {lot.roomKey && (
                <p className="mt-3">
                  <Link
                    href={`/play?room=${encodeURIComponent(lot.roomKey)}`}
                    className="font-mono text-[12px] text-sky-700 underline dark:text-sky-400"
                  >
                    Visit room →
                  </Link>
                </p>
              )}
            </section>
          ) : (
            <p className="font-mono text-[12px] text-amber-800 dark:text-amber-400">
              No parcel record is linked to this deed (lot_ref missing).
            </p>
          )}
        </div>
      )}
    </main>
  );
}
