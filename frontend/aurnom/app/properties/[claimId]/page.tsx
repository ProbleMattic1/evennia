"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { PropertyDeedMarketPanel } from "@/components/property-deed-market-panel";
import {
  getPropertyClaimDetail,
  installPropertyStructure,
  purchasePropertyExtraSlot,
  purchasePropertyStructureUpgrade,
  retoolPropertyOperation,
  setPropertyOperationPaused,
  startPropertyOperation,
  type PropertyClaimDetailState,
  type PropertyHoldingStructure,
  type PropertyStructureUpgradeCatalogEntry,
} from "@/lib/ui-api";

function nextStructureUpgradeOffer(
  structure: PropertyHoldingStructure,
  def: PropertyStructureUpgradeCatalogEntry,
): { nextLevel: number; priceCr: number } | null {
  const bid = structure.blueprintId;
  if (def.allowedBlueprintIds != null && def.allowedBlueprintIds.length > 0) {
    if (!bid || !def.allowedBlueprintIds.includes(bid)) return null;
  }
  const cur = structure.upgrades[def.upgradeKey] ?? 0;
  if (cur >= def.maxLevel) return null;
  const nextLevel = cur + 1;
  const priceCr = def.levelCostCr[String(nextLevel)];
  if (priceCr == null) return null;
  return { nextLevel, priceCr };
}

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
  const [startBusy, setStartBusy] = useState(false);
  const [startErr, setStartErr] = useState<string | null>(null);
  const [opKindChoice, setOpKindChoice] = useState<string>("");
  const [buildBlueprintId, setBuildBlueprintId] = useState("");
  const [buildBusy, setBuildBusy] = useState(false);
  const [buildErr, setBuildErr] = useState<string | null>(null);
  const [pauseBusy, setPauseBusy] = useState(false);
  const [pauseErr, setPauseErr] = useState<string | null>(null);
  const [retoolKind, setRetoolKind] = useState("");
  const [retoolBusy, setRetoolBusy] = useState(false);
  const [retoolErr, setRetoolErr] = useState<string | null>(null);
  const [extraSlotBusy, setExtraSlotBusy] = useState(false);
  const [extraSlotErr, setExtraSlotErr] = useState<string | null>(null);
  const [upgradeErr, setUpgradeErr] = useState<string | null>(null);
  const [upgradingKey, setUpgradingKey] = useState<string | null>(null);

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

  useEffect(() => {
    if (typeof window === "undefined" || loading) return;
    if (!data?.ok) return;
    if (window.location.hash !== "#property-deed-resale") return;
    const el = document.getElementById("property-deed-resale");
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [loading, data?.ok, claimId]);

  useEffect(() => {
    const d = data?.holding?.defaultOperationKind;
    if (d) setOpKindChoice(d);
  }, [data?.holding?.holdingId, data?.holding?.defaultOperationKind]);

  useEffect(() => {
    const h = data?.holding;
    const cur = h?.operation?.kind;
    if (!h || !cur) {
      setRetoolKind("");
      return;
    }
    const opts = h.allowedOperationKinds.filter((k) => k !== cur);
    if (opts.length === 0) {
      setRetoolKind("");
      return;
    }
    setRetoolKind((prev) => (opts.includes(prev) ? prev : opts[0]!));
  }, [data?.holding?.holdingId, data?.holding?.operation?.kind, data?.holding?.allowedOperationKinds]);

  useEffect(() => {
    const cat = data?.holding?.buildCatalog;
    if (!cat?.length) {
      setBuildBlueprintId("");
      return;
    }
    setBuildBlueprintId((prev) => (cat.some((r) => r.id === prev) ? prev : cat[0]!.id));
  }, [data?.holding?.holdingId, data?.holding?.buildCatalog]);

  const claim = data?.claim;
  const lot = data?.lot;
  const holding = data?.holding;

  async function handleStartOperation() {
    if (!holding || !Number.isFinite(claimId)) return;
    setStartErr(null);
    setStartBusy(true);
    try {
      const kinds = holding.allowedOperationKinds;
      const kind = kinds.length > 1 ? opKindChoice : undefined;
      await startPropertyOperation({ claimId, ...(kind ? { kind } : {}) });
      await load();
    } catch (e) {
      setStartErr(e instanceof Error ? e.message : "Could not start operation.");
    } finally {
      setStartBusy(false);
    }
  }

  async function handleInstallStructure() {
    if (!holding || !Number.isFinite(claimId) || !buildBlueprintId) return;
    setBuildErr(null);
    setBuildBusy(true);
    try {
      await installPropertyStructure({ claimId, blueprintId: buildBlueprintId });
      await load();
    } catch (e) {
      setBuildErr(e instanceof Error ? e.message : "Could not install structure.");
    } finally {
      setBuildBusy(false);
    }
  }

  async function handlePauseToggle(paused: boolean) {
    if (!holding || !Number.isFinite(claimId)) return;
    setPauseErr(null);
    setPauseBusy(true);
    try {
      await setPropertyOperationPaused({ claimId, paused });
      await load();
    } catch (e) {
      setPauseErr(e instanceof Error ? e.message : "Could not update pause state.");
    } finally {
      setPauseBusy(false);
    }
  }

  async function handleRetool() {
    if (!holding || !Number.isFinite(claimId) || !retoolKind) return;
    setRetoolErr(null);
    setRetoolBusy(true);
    try {
      await retoolPropertyOperation({ claimId, kind: retoolKind });
      await load();
    } catch (e) {
      setRetoolErr(e instanceof Error ? e.message : "Could not retool.");
    } finally {
      setRetoolBusy(false);
    }
  }

  async function handlePurchaseExtraSlot() {
    if (!holding || !Number.isFinite(claimId)) return;
    setExtraSlotErr(null);
    setExtraSlotBusy(true);
    try {
      await purchasePropertyExtraSlot({ claimId });
      await load();
    } catch (e) {
      setExtraSlotErr(e instanceof Error ? e.message : "Could not purchase slot.");
    } finally {
      setExtraSlotBusy(false);
    }
  }

  async function handleStructureUpgrade(structureId: number, upgradeKey: string) {
    if (!holding || !Number.isFinite(claimId)) return;
    setUpgradeErr(null);
    setUpgradingKey(`${structureId}-${upgradeKey}`);
    try {
      await purchasePropertyStructureUpgrade({ claimId, structureId, upgradeKey });
      await load();
    } catch (e) {
      setUpgradeErr(e instanceof Error ? e.message : "Could not purchase upgrade.");
    } finally {
      setUpgradingKey(null);
    }
  }

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
            {holding ? (
              <p className="mt-3 border-t border-zinc-200 pt-2 text-[11px] text-zinc-600 dark:border-cyan-900/40 dark:text-zinc-400">
                In-game <span className="font-mono">give</span> to another character charges{" "}
                <span className="font-mono tabular-nums">
                  {holding.deedTransferFeeCr.toLocaleString()} cr
                </span>{" "}
                (transfer fee). List or buy in the{" "}
                <Link
                  href={`/properties/${claim.id}#property-deed-resale`}
                  className="text-sky-700 underline dark:text-sky-400"
                >
                  deed resale section
                </Link>{" "}
                below.
              </p>
            ) : null}
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

          <section className="rounded border border-zinc-200 bg-white p-3 dark:border-cyan-900/50 dark:bg-zinc-900/40">
            <h2 className="section-label">Development</h2>
            {!holding ? (
              <p className="mt-2 font-mono text-[12px] text-amber-800 dark:text-amber-400">
                No holding linked to this parcel (legacy or missing record).
              </p>
            ) : (
              <div className="mt-2 space-y-3 text-sm">
                <dl className="grid gap-1">
                  <div className="flex justify-between gap-2">
                    <dt className="text-zinc-500">Holding</dt>
                    <dd className="font-mono text-zinc-800 dark:text-zinc-200">#{holding.holdingId}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-zinc-500">State</dt>
                    <dd className="font-mono text-zinc-800 dark:text-zinc-200">
                      {holding.developmentState}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-zinc-500">Operation</dt>
                    <dd className="font-mono text-zinc-800 dark:text-zinc-200">
                      {holding.operation.kind ?? "—"}
                      {holding.operation.paused ? " (paused)" : ""}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-zinc-500">Next tick (UTC)</dt>
                    <dd className="font-mono text-right text-[11px] text-zinc-700 dark:text-zinc-300">
                      {holding.operation.nextTickAt ?? "—"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-zinc-500">Income accrued (ledger)</dt>
                    <dd className="font-mono tabular-nums text-zinc-800 dark:text-zinc-200">
                      {holding.ledger.creditsAccrued.toLocaleString()} cr
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-zinc-500">Last tick</dt>
                    <dd className="font-mono text-right text-[11px] text-zinc-600 dark:text-zinc-400">
                      {holding.ledger.lastTickIso ?? "—"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-zinc-500">Place</dt>
                    <dd className="font-mono text-zinc-800 dark:text-zinc-200">
                      {holding.place.mode}
                      {holding.place.rootRoomId != null ? ` · room #${holding.place.rootRoomId}` : ""}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-zinc-500">Structure slots</dt>
                    <dd className="font-mono tabular-nums text-zinc-800 dark:text-zinc-200">
                      {holding.structureSlotsUsed} / {holding.structureSlotsTotal}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-zinc-500">Event queue</dt>
                    <dd className="font-mono text-zinc-800 dark:text-zinc-200">
                      {holding.eventQueueLength} (showing last {holding.eventQueuePreview.length})
                    </dd>
                  </div>
                </dl>

                <div className="border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                  {extraSlotErr ? (
                    <p className="mb-2 font-mono text-[12px] text-red-600 dark:text-red-400">
                      {extraSlotErr}
                    </p>
                  ) : null}
                  <button
                    type="button"
                    disabled={extraSlotBusy}
                    onClick={() => void handlePurchaseExtraSlot()}
                    className="rounded bg-slate-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-slate-600 disabled:opacity-50 dark:bg-slate-600 dark:hover:bg-slate-500"
                  >
                    {extraSlotBusy
                      ? "…"
                      : `Buy +1 structure slot (${holding.nextExtraStructureSlotPriceCr.toLocaleString()} cr)`}
                  </button>
                  <p className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-500">
                    In-game: <span className="font-mono">buypropertyslot</span>
                  </p>
                </div>

                {upgradeErr ? (
                  <p className="font-mono text-[12px] text-red-600 dark:text-red-400">{upgradeErr}</p>
                ) : null}

                {holding.structures.length > 0 ? (
                  <div>
                    <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
                      Structures
                    </p>
                    <ul className="mt-2 flex flex-col gap-2">
                      {holding.structures.map((s) => (
                        <li
                          key={s.id}
                          className="list-none rounded border border-zinc-200 px-2 py-2 font-mono text-[11px] text-zinc-600 dark:border-cyan-900/40 dark:text-zinc-400"
                        >
                          <div>
                            <span className="text-zinc-800 dark:text-zinc-200">{s.key}</span>
                            {s.blueprintId ? ` · ${s.blueprintId}` : ""} · #{s.id} · slots {s.slotWeight}{" "}
                            · cond {s.condition}
                          </div>
                          {Object.keys(s.upgrades).length > 0 ? (
                            <div className="mt-1 text-[10px] text-zinc-500">
                              Upgrades:{" "}
                              {Object.entries(s.upgrades)
                                .map(([k, v]) => `${k} L${v}`)
                                .join(", ")}
                            </div>
                          ) : null}
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {(holding.structureUpgradeCatalog ?? []).map((def) => {
                              const offer = nextStructureUpgradeOffer(s, def);
                              if (!offer) return null;
                              const ukey = `${s.id}-${def.upgradeKey}`;
                              return (
                                <button
                                  key={def.upgradeKey}
                                  type="button"
                                  disabled={upgradingKey === ukey}
                                  onClick={() => void handleStructureUpgrade(s.id, def.upgradeKey)}
                                  className="rounded border border-zinc-300 bg-zinc-100 px-2 py-1 text-[10px] font-semibold text-zinc-800 hover:bg-zinc-200 disabled:opacity-50 dark:border-cyan-800 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
                                >
                                  {upgradingKey === ukey
                                    ? "…"
                                    : `${def.upgradeKey} → L${offer.nextLevel} (${offer.priceCr.toLocaleString()} cr)`}
                                </button>
                              );
                            })}
                          </div>
                        </li>
                      ))}
                    </ul>
                    <p className="mt-2 text-[11px] text-zinc-500 dark:text-zinc-500">
                      In-game: <span className="font-mono">upgradeproperty</span> &lt;structure id&gt;{" "}
                      &lt;upgrade_key&gt;
                    </p>
                  </div>
                ) : null}

                {holding.eventQueuePreview.length > 0 ? (
                  <details className="text-[11px] text-zinc-600 dark:text-zinc-400">
                    <summary className="cursor-pointer font-mono">Event preview</summary>
                    <pre className="mt-1 max-h-40 overflow-auto rounded bg-zinc-100 p-2 dark:bg-zinc-950">
                      {JSON.stringify(holding.eventQueuePreview, null, 2)}
                    </pre>
                  </details>
                ) : null}

                {(holding.buildCatalog?.length ?? 0) > 0 ? (
                  <div className="border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                    <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
                      Build (catalog)
                    </p>
                    {buildErr ? (
                      <p className="mb-2 font-mono text-[12px] text-red-600 dark:text-red-400">
                        {buildErr}
                      </p>
                    ) : null}
                    <div className="mt-2 flex flex-wrap items-end gap-2">
                      <label className="flex flex-col gap-0.5 font-mono text-[12px] text-zinc-600 dark:text-zinc-400">
                        Blueprint
                        <select
                          value={buildBlueprintId}
                          onChange={(ev) => setBuildBlueprintId(ev.target.value)}
                          className="min-w-[12rem] rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-zinc-200"
                        >
                          {(holding.buildCatalog ?? []).map((row) => (
                            <option key={row.id} value={row.id}>
                              {row.name} — {row.priceCr.toLocaleString()} cr · slots {row.slotWeight}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        type="button"
                        disabled={buildBusy || !buildBlueprintId}
                        onClick={() => void handleInstallStructure()}
                        className="rounded bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-600 disabled:opacity-50 dark:bg-emerald-800 dark:hover:bg-emerald-700"
                      >
                        {buildBusy ? "Installing…" : "Install structure"}
                      </button>
                    </div>
                    <p className="mt-2 text-[11px] text-zinc-500 dark:text-zinc-500">
                      In-game: <span className="font-mono">buildproperty</span> &lt;blueprintId&gt;
                    </p>
                  </div>
                ) : null}

                {!holding.operation.kind ? (
                  <div className="border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                    {startErr ? (
                      <p className="mb-2 font-mono text-[12px] text-red-600 dark:text-red-400">
                        {startErr}
                      </p>
                    ) : null}
                    {holding.allowedOperationKinds.length > 1 ? (
                      <label className="mb-2 flex flex-wrap items-center gap-2 font-mono text-[12px] text-zinc-600 dark:text-zinc-400">
                        Operation kind
                        <select
                          value={opKindChoice}
                          onChange={(ev) => setOpKindChoice(ev.target.value)}
                          className="rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-zinc-200"
                        >
                          {holding.allowedOperationKinds.map((k) => (
                            <option key={k} value={k}>
                              {k}
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : null}
                    <button
                      type="button"
                      disabled={startBusy}
                      onClick={() => void handleStartOperation()}
                      className="rounded bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-50 dark:bg-cyan-700 dark:hover:bg-cyan-600"
                    >
                      {startBusy ? "Starting…" : "Start income"}
                    </button>
                    <p className="mt-2 text-[11px] text-zinc-500 dark:text-zinc-500">
                      Default for this zone: {holding.defaultOperationKind ?? "—"}. In-game:{" "}
                      <span className="font-mono">startproperty</span>.
                    </p>
                  </div>
                ) : (
                  <div className="border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                    {pauseErr ? (
                      <p className="mb-2 font-mono text-[12px] text-red-600 dark:text-red-400">
                        {pauseErr}
                      </p>
                    ) : null}
                    {retoolErr ? (
                      <p className="mb-2 font-mono text-[12px] text-red-600 dark:text-red-400">
                        {retoolErr}
                      </p>
                    ) : null}
                    <button
                      type="button"
                      disabled={pauseBusy}
                      onClick={() => void handlePauseToggle(!holding.operation.paused)}
                      className="rounded bg-zinc-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-zinc-600 disabled:opacity-50 dark:bg-zinc-600 dark:hover:bg-zinc-500"
                    >
                      {pauseBusy ? "…" : holding.operation.paused ? "Resume income" : "Pause income"}
                    </button>
                    {(() => {
                      const cur = holding.operation.kind;
                      const opts = holding.allowedOperationKinds.filter((k) => k !== cur);
                      if (opts.length === 0) {
                        return (
                          <p className="mt-2 font-mono text-[11px] text-zinc-500 dark:text-zinc-500">
                            No alternate operation type for this zone. In-game:{" "}
                            <span className="font-mono">pauseproperty</span> /{" "}
                            <span className="font-mono">resumeproperty</span> /{" "}
                            <span className="font-mono">retoolproperty</span>.
                          </p>
                        );
                      }
                      return (
                        <div className="mt-3 space-y-2">
                          <label className="flex flex-wrap items-center gap-2 font-mono text-[12px] text-zinc-600 dark:text-zinc-400">
                            Retool to
                            <select
                              value={retoolKind}
                              onChange={(ev) => setRetoolKind(ev.target.value)}
                              className="rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-zinc-200"
                            >
                              {opts.map((k) => (
                                <option key={k} value={k}>
                                  {k}
                                </option>
                              ))}
                            </select>
                          </label>
                          <button
                            type="button"
                            disabled={retoolBusy || !retoolKind}
                            onClick={() => void handleRetool()}
                            className="rounded bg-amber-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-600 disabled:opacity-50 dark:bg-amber-800 dark:hover:bg-amber-700"
                          >
                            {retoolBusy
                              ? "Retooling…"
                              : `Retool (${holding.retoolFeeCr.toLocaleString()} cr)`}
                          </button>
                          <p className="text-[11px] text-zinc-500 dark:text-zinc-500">
                            In-game:{" "}
                            <span className="font-mono">retoolproperty</span> &lt;kind&gt; [optional deed
                            fragment]
                          </p>
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
            )}
          </section>

          <section
            id="property-deed-resale"
            aria-label="Property deed resale"
            className="scroll-mt-4"
          >
            <PropertyDeedMarketPanel defaultClaimId={claim.id} />
          </section>
        </div>
      )}
    </main>
  );
}
