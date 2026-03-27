"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CsButtonLink, CsColumns, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { StoryPanel } from "@/components/story-panel";
import {
  getClaimDetail,
  listClaimForSale,
  type ClaimDetailState,
} from "@/lib/ui-api";
import { volumeTierStyle, rarityTierStyle } from "@/lib/mine-tier-styles";

export default function ClaimDetailPage() {
  const params = useParams();
  const router = useRouter();
  const raw = params.claimId;
  const claimId = Number(Array.isArray(raw) ? raw[0] : raw);

  const [data, setData] = useState<ClaimDetailState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [price, setPrice] = useState("");
  const [listBusy, setListBusy] = useState(false);
  const [listMsg, setListMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!Number.isFinite(claimId)) {
      setError("Invalid claim.");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await getClaimDetail(claimId);
      if (!res.ok) {
        setError(res.message ?? "Unable to load claim.");
        setData(null);
      } else {
        setData(res);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load claim.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [claimId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleList() {
    if (!Number.isFinite(claimId) || listBusy) return;
    const p = parseInt(price, 10);
    if (Number.isNaN(p) || p < 0) {
      setListMsg("Enter a valid non-negative price.");
      return;
    }
    setListMsg(null);
    setListBusy(true);
    try {
      const res = await listClaimForSale({ claimId, price: p });
      setListMsg(res.message ?? "Listed.");
      router.push("/real-estate#claims-market");
      router.refresh();
    } catch (e) {
      setListMsg(e instanceof Error ? e.message : "List failed.");
    } finally {
      setListBusy(false);
    }
  }

  const site = data?.site;
  const volT = volumeTierStyle(site?.volumeTierCls);
  const rarT = rarityTierStyle(site?.resourceRarityTierCls);

  return (
    <CsPage>
      <CsHeader
        title={data?.claim?.key ?? "Claim"}
        subtitle={data?.claim?.description ?? "Mining claim deed"}
        actions={
          <>
            <CsButtonLink href="/">Dashboard</CsButtonLink>
            <CsButtonLink href="/real-estate#claims-market">Claims Market</CsButtonLink>
          </>
        }
      />

      {loading && <p className="px-2 py-3 font-mono text-sm text-zinc-500">Loading…</p>}
      {error && <p className="px-2 py-3 font-mono text-sm text-red-600">{error}</p>}

      {data?.ok && site ? (
        <CsColumns
          left={
            <>
              <CsPanel title="Claim Output">
                <StoryPanel title="Claim Output" lines={data.storyLines ?? []} compact />
              </CsPanel>
              <CsPanel title="Deposit">
              <dl className="mt-2 grid gap-1 text-sm">
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">Location</dt>
                  <dd className="font-mono text-zinc-200">{site.roomKey}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">Volume</dt>
                  <dd>
                    <span className={`rounded px-1.5 py-0.5 font-mono text-[12px] ${volT.badge}`}>{site.volumeTier}</span>
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">Rarity</dt>
                  <dd>
                    <span className={`rounded px-1.5 py-0.5 font-mono text-[12px] ${rarT.badge}`}>
                      {site.resourceRarityTier}
                    </span>
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">Hazard</dt>
                  <dd className="font-mono">{site.hazardLabel}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-zinc-500">Allowed purposes</dt>
                  <dd className="text-right font-mono text-[12px]">
                    {(data.claim?.allowedPurposes ?? ["mining"]).join(", ")}
                  </dd>
                </div>
              </dl>
              <p className="mt-3">
                <Link
                  href="/"
                  className="font-mono text-[12px] text-sky-700 underline dark:text-sky-400"
                >
                  Visit site →
                </Link>
              </p>
              </CsPanel>
            </>
          }
          right={
            <>
              {data.isOwner && !data.isListed ? (
                <CsPanel title="Sell Deed">
                  <p className="mt-1 text-[12px] text-zinc-500">
                    List this claim on the claims market at your price (escrow until sold).
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <input
                      type="number"
                      min={0}
                      className="w-32 rounded border border-zinc-300 bg-white px-2 py-1 font-mono text-sm text-zinc-900 dark:border-cyan-800 dark:bg-zinc-950 dark:text-zinc-100"
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                      placeholder="Price (cr)"
                    />
                    <button
                      type="button"
                      className="rounded border border-zinc-300 bg-zinc-100 px-2 py-1 font-mono text-[12px] text-zinc-900 dark:border-cyan-800 dark:bg-cyan-950/50 dark:text-zinc-100"
                      disabled={listBusy}
                      onClick={() => void handleList()}
                    >
                      {listBusy ? "Listing…" : "List for sale"}
                    </button>
                  </div>
                  {listMsg ? <p className="mt-2 font-mono text-[12px] text-zinc-500">{listMsg}</p> : null}
                </CsPanel>
              ) : null}
              <CsPanel title="Status">
                {data.isListed ? (
                  <p className="font-mono text-[12px] text-amber-800 dark:text-amber-400">
                    This deed is listed on the{" "}
                    <Link href="/real-estate#claims-market" className="underline">
                      claims market
                    </Link>
                    .
                  </p>
                ) : (
                  <p className="font-mono text-[12px] text-zinc-500">Not currently listed on claims market.</p>
                )}
                <p className="mt-2 text-[12px] text-zinc-500">
                  <Link href="/" className="underline">
                    Home dashboard
                  </Link>{" "}
                  — deploy a mining package with this claim when you are ready.
                </p>
              </CsPanel>
            </>
          }
        />
      ) : null}
    </CsPage>
  );
}
