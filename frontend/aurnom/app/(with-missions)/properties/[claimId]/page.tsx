"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CsButtonLink, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { VenueBillboardStoryFrame } from "@/components/venue-billboard-story-frame";
import { PropertyDeedListForm } from "@/components/property-deed-list-form";
import {
  EMPTY_ROOM_AMBIENT,
  getPropertyClaimDetail,
  installPropertyStructure,
  propertyProcessorDeploy,
  propertyWorkshopCollect,
  propertyWorkshopFeed,
  propertyWorkshopQueue,
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
  const [fabWorkshopId, setFabWorkshopId] = useState<number | null>(null);
  const [fabRecipeKey, setFabRecipeKey] = useState("");
  const [fabRuns, setFabRuns] = useState("1");
  const [fabProductKey, setFabProductKey] = useState("");
  const [fabUnits, setFabUnits] = useState("");
  const [fabHoldingOnly, setFabHoldingOnly] = useState(true);
  const [fabCollectKey, setFabCollectKey] = useState("");
  const [workshopPanelErr, setWorkshopPanelErr] = useState<string | null>(null);
  const [workshopQueueBusy, setWorkshopQueueBusy] = useState(false);
  const [workshopFeedBusy, setWorkshopFeedBusy] = useState(false);
  const [workshopCollectBusy, setWorkshopCollectBusy] = useState(false);
  const [processorDeployBusy, setProcessorDeployBusy] = useState(false);
  const [processorDeployErr, setProcessorDeployErr] = useState<string | null>(null);
  const [processorDeployId, setProcessorDeployId] = useState<number | null>(null);

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
    const rows = data?.portableProcessorsCarried ?? [];
    if (!rows.length) {
      setProcessorDeployId(null);
      return;
    }
    setProcessorDeployId((cur) =>
      cur != null && rows.some((r) => r.id === cur) ? cur : rows[0]!.id,
    );
  }, [data?.portableProcessorsCarried]);

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

  useEffect(() => {
    const ws = data?.holding?.workshops ?? [];
    if (!ws.length) {
      setFabWorkshopId(null);
      return;
    }
    setFabWorkshopId((cur) =>
      cur != null && ws.some((w) => w.workshopId === cur) ? cur : ws[0]!.workshopId,
    );
  }, [data?.holding?.holdingId, data?.holding?.workshops]);

  useEffect(() => {
    const h = data?.holding;
    if (!h?.workshops?.length) return;
    const ws = h.workshops.find((w) => w.workshopId === fabWorkshopId);
    const recipes = (h.manufacturingRecipes ?? []).filter((r) => r.stationKind === ws?.stationKind);
    if (!recipes.length) {
      setFabRecipeKey("");
      return;
    }
    setFabRecipeKey((prev) => (recipes.some((r) => r.id === prev) ? prev : recipes[0]!.id));
  }, [
    data?.holding?.holdingId,
    fabWorkshopId,
    data?.holding?.manufacturingRecipes,
    data?.holding?.workshops,
  ]);

  useEffect(() => {
    setFabCollectKey("");
  }, [fabWorkshopId, data?.holding?.holdingId]);

  useEffect(() => {
    const h = data?.holding;
    if (!h) return;
    const rows = fabHoldingOnly
      ? (h.manufacturingFeedStockHoldingOnly ?? [])
      : (h.manufacturingFeedStockWithRoom ?? []);
    if (!rows.length) {
      setFabProductKey("");
      setFabUnits("");
      return;
    }
    if (!fabProductKey || !rows.some((r) => r.productKey === fabProductKey)) {
      const r0 = rows[0]!;
      setFabProductKey(r0.productKey);
      setFabUnits(String(r0.unitsAvailable));
    }
  }, [
    data?.holding?.holdingId,
    fabHoldingOnly,
    fabProductKey,
    data?.holding?.manufacturingFeedStockHoldingOnly,
    data?.holding?.manufacturingFeedStockWithRoom,
  ]);

  const claim = data?.claim;
  const lot = data?.lot;
  const holding = data?.holding;

  const selectedFabWorkshop =
    holding?.workshops?.find((w) => w.workshopId === fabWorkshopId) ?? null;
  const fabRecipeOptions =
    holding && selectedFabWorkshop
      ? (holding.manufacturingRecipes ?? []).filter(
          (r) => r.stationKind === selectedFabWorkshop.stationKind,
        )
      : [];
  const fabFeedRows = holding
    ? fabHoldingOnly
      ? (holding.manufacturingFeedStockHoldingOnly ?? [])
      : (holding.manufacturingFeedStockWithRoom ?? [])
    : [];

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

  async function handleWorkshopQueue() {
    if (!holding || !Number.isFinite(claimId) || fabWorkshopId == null) return;
    setWorkshopPanelErr(null);
    setWorkshopQueueBusy(true);
    try {
      const runs = Math.max(1, parseInt(fabRuns, 10) || 1);
      await propertyWorkshopQueue({
        claimId,
        workshopId: fabWorkshopId,
        recipeKey: fabRecipeKey,
        runs,
      });
      await load();
    } catch (e) {
      setWorkshopPanelErr(e instanceof Error ? e.message : "Queue failed.");
    } finally {
      setWorkshopQueueBusy(false);
    }
  }

  async function handleWorkshopFeed() {
    if (!holding || !Number.isFinite(claimId) || fabWorkshopId == null) return;
    setWorkshopPanelErr(null);
    setWorkshopFeedBusy(true);
    try {
      const rows = fabHoldingOnly
        ? (holding.manufacturingFeedStockHoldingOnly ?? [])
        : (holding.manufacturingFeedStockWithRoom ?? []);
      const cap = rows.find((r) => r.productKey === fabProductKey)?.unitsAvailable;
      let units = parseFloat(fabUnits);
      if (!Number.isFinite(units) || units <= 0) {
        setWorkshopPanelErr("Units must be a positive number.");
        return;
      }
      if (cap != null && units > cap) {
        units = cap;
      }
      await propertyWorkshopFeed({
        claimId,
        workshopId: fabWorkshopId,
        productKey: fabProductKey,
        units,
        holdingSourcesOnly: fabHoldingOnly,
      });
      await load();
    } catch (e) {
      setWorkshopPanelErr(e instanceof Error ? e.message : "Feed failed.");
    } finally {
      setWorkshopFeedBusy(false);
    }
  }

  async function handleWorkshopCollect() {
    if (!holding || !Number.isFinite(claimId) || fabWorkshopId == null) return;
    setWorkshopPanelErr(null);
    setWorkshopCollectBusy(true);
    try {
      await propertyWorkshopCollect({
        claimId,
        workshopId: fabWorkshopId,
        ...(fabCollectKey ? { productKey: fabCollectKey } : {}),
      });
      await load();
    } catch (e) {
      setWorkshopPanelErr(e instanceof Error ? e.message : "Collect failed.");
    } finally {
      setWorkshopCollectBusy(false);
    }
  }

  async function handleProcessorDeploy() {
    if (!holding || !Number.isFinite(claimId) || processorDeployId == null) return;
    setProcessorDeployErr(null);
    setProcessorDeployBusy(true);
    try {
      await propertyProcessorDeploy({ claimId, processorId: processorDeployId });
      await load();
    } catch (e) {
      setProcessorDeployErr(e instanceof Error ? e.message : "Deploy failed.");
    } finally {
      setProcessorDeployBusy(false);
    }
  }

  return (
    <CsPage>
      <CsHeader
        title={claim?.key ?? "Property claim"}
        subtitle={claim?.description ?? "Property deed"}
        actions={
          <>
            <CsButtonLink href="/real-estate">Real Estate Office</CsButtonLink>
            <CsButtonLink href="/" variant="dashboard">
              Home
            </CsButtonLink>
          </>
        }
      />
      {data?.ok && data.roomName ? (
        <VenueBillboardStoryFrame
          panelTitle="Location & story"
          roomName={data.roomName}
          ambient={data.ambient ?? EMPTY_ROOM_AMBIENT}
          storyLines={data.storyLines ?? []}
          storySubheading="Deed output"
        />
      ) : null}

      {loading && <p className="px-2 py-3 font-mono text-sm text-ui-muted">Loading…</p>}
      {error && <p className="px-2 py-3 font-mono text-sm text-red-600 dark:text-red-400">{error}</p>}

      {data?.ok && claim && (
        <div className="min-h-0 min-w-0 overflow-y-auto p-1.5 md:min-h-0">
              <CsPanel title="Deed">
            <dl className="mt-2 grid gap-1 text-sm">
              <div className="flex justify-between gap-2">
                <dt className="text-ui-muted">Kind</dt>
                <dd className="font-mono text-zinc-800 dark:text-foreground">
                  {KIND_LABEL[claim.kind] ?? claim.kind}
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-ui-muted">Parcel</dt>
                <dd className="font-mono text-zinc-800 dark:text-foreground">{claim.lotKey || "—"}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-ui-muted">Tier (on deed)</dt>
                <dd className="font-mono text-zinc-800 dark:text-foreground">{claim.lotTier}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-ui-muted">Object ID</dt>
                <dd className="font-mono text-zinc-800 dark:text-foreground">#{claim.id}</dd>
              </div>
            </dl>
            {holding ? (
              <p className="mt-3 border-t border-cyan-900/40 pt-2 text-xs text-ui-muted">
                In-game <span className="font-mono">give</span> to another character charges{" "}
                <span className="font-mono tabular-nums">
                  {holding.deedTransferFeeCr.toLocaleString()}cr
                </span>{" "}
                (transfer fee). List below; buy player-listed deeds on the{" "}
                <Link
                  href="/real-estate#property-deed-resale-market"
                  className="text-sky-700 underline dark:text-sky-400"
                >
                  Real Estate office
                </Link>
                .
              </p>
            ) : null}
              </CsPanel>

              {lot ? (
                <CsPanel title="Parcel">
              <dl className="mt-2 grid gap-1 text-sm">
                <div className="flex justify-between gap-2">
                  <dt className="text-ui-muted">Lot</dt>
                  <dd className="font-mono text-zinc-800 dark:text-foreground">{lot.lotKey}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-ui-muted">Zone</dt>
                  <dd className="text-zinc-800 dark:text-foreground">{lot.zoneLabel}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-ui-muted">Tier</dt>
                  <dd className="font-mono text-zinc-800 dark:text-foreground">
                    {lot.tierLabel} ({lot.tier})
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-ui-muted">Size (units)</dt>
                  <dd className="font-mono text-zinc-800 dark:text-foreground">{lot.sizeUnits}</dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-ui-muted">Claimed</dt>
                  <dd className="font-mono text-zinc-800 dark:text-foreground">
                    {lot.isClaimed ? "Yes" : "No"}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-ui-muted">Recorded owner</dt>
                  <dd className="font-mono text-right text-xs text-zinc-800 dark:text-foreground">
                    {lot.ownerKey ?? "—"}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-ui-muted">Sovereign list price (reference)</dt>
                  <dd className="font-mono tabular-nums text-zinc-800 dark:text-foreground">
                    {lot.referenceListPriceCr.toLocaleString()}cr
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-ui-muted">On primary market</dt>
                  <dd className="font-mono text-zinc-800 dark:text-foreground">
                    {lot.purchasable ? "Yes" : "No"}
                  </dd>
                </div>
                {lot.roomKey && (
                  <div className="flex justify-between gap-2">
                    <dt className="text-ui-muted">Room</dt>
                    <dd className="font-mono text-right text-xs text-zinc-800 dark:text-foreground">
                      {lot.roomKey}
                    </dd>
                  </div>
                )}
              </dl>
              {lot.description && (
                <p className="mt-3 border-t border-zinc-100 pt-3 text-xs text-ui-muted dark:border-cyan-900/40">
                  {lot.description}
                </p>
              )}
              {lot.roomKey && (
                <p className="mt-3">
                  <Link
                    href="/"
                    className="font-mono text-xs text-sky-700 underline dark:text-sky-400"
                  >
                    Visit room →
                  </Link>
                </p>
              )}
                </CsPanel>
              ) : (
                <CsPanel title="Parcel">
                  <p className="font-mono text-xs text-amber-800 dark:text-amber-400">
                    No parcel record is linked to this deed (lot_ref missing).
                  </p>
                </CsPanel>
              )}
              <CsPanel title="Development">
            {!holding ? (
              <p className="mt-2 font-mono text-xs text-amber-800 dark:text-amber-400">
                No holding linked to this parcel (legacy or missing record).
              </p>
            ) : (
              <div className="mt-2 space-y-3 text-sm">
                <dl className="grid gap-1">
                  <div className="flex justify-between gap-2">
                    <dt className="text-ui-muted">Holding</dt>
                    <dd className="font-mono text-zinc-800 dark:text-foreground">#{holding.holdingId}</dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ui-muted">State</dt>
                    <dd className="font-mono text-zinc-800 dark:text-foreground">
                      {holding.developmentState}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ui-muted">Operation</dt>
                    <dd className="font-mono text-zinc-800 dark:text-foreground">
                      {holding.operation.kind ?? "—"}
                      {holding.operation.paused ? " (paused)" : ""}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ui-muted">Next tick (UTC)</dt>
                    <dd className="font-mono text-right text-xs text-zinc-700 dark:text-foreground">
                      {holding.operation.nextTickAt ?? "—"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ui-muted">Income accrued (ledger)</dt>
                    <dd className="font-mono tabular-nums text-zinc-800 dark:text-foreground">
                      {holding.ledger.creditsAccrued.toLocaleString()}cr
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ui-muted">Last tick</dt>
                    <dd className="font-mono text-right text-xs text-ui-muted">
                      {holding.ledger.lastTickIso ?? "—"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ui-muted">Place</dt>
                    <dd className="font-mono text-zinc-800 dark:text-foreground">
                      {holding.place.mode}
                      {holding.place.rootRoomId != null ? ` · room #${holding.place.rootRoomId}` : ""}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ui-muted">Structure slots</dt>
                    <dd className="font-mono tabular-nums text-zinc-800 dark:text-foreground">
                      {holding.structureSlotsUsed} / {holding.structureSlotsTotal}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-ui-muted">Event queue</dt>
                    <dd className="font-mono text-zinc-800 dark:text-foreground">
                      {holding.eventQueueLength} (showing last {holding.eventQueuePreview.length})
                    </dd>
                  </div>
                </dl>

                <div className="border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                  {extraSlotErr ? (
                    <p className="mb-2 font-mono text-xs text-red-600 dark:text-red-400">
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
                      : `Buy +1 structure slot (${holding.nextExtraStructureSlotPriceCr.toLocaleString()}cr)`}
                  </button>
                  <p className="mt-1 text-xs text-ui-muted">
                    In-game: <span className="font-mono">buypropertyslot</span>
                  </p>
                </div>

                <div className="border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                  <p className="text-xs font-medium uppercase tracking-wide text-ui-muted">
                    Portable ore processor
                  </p>
                  <p className="mt-1 text-xs text-ui-muted">
                    Installs the unit into this deed&apos;s parcel interior. You do not need to stand
                    there. Use <span className="font-mono">visitproperty</span> when you want to be
                    there in person (same as <span className="font-mono">drop</span> when you are
                    already inside).
                  </p>
                  {(data?.portableProcessorsCarried?.length ?? 0) === 0 ? (
                    <p className="mt-2 font-mono text-xs text-ui-muted">
                      No portable ore processor in inventory.
                    </p>
                  ) : (
                    <div className="mt-2 flex flex-wrap items-end gap-2">
                      <label className="flex flex-col gap-0.5 font-mono text-xs text-ui-muted">
                        Processor
                        <select
                          value={processorDeployId ?? ""}
                          onChange={(ev) => setProcessorDeployId(Number(ev.target.value))}
                          className="min-w-[12rem] max-w-[20rem] rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-foreground"
                        >
                          {(data?.portableProcessorsCarried ?? []).map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.key} · Mk {p.mk} · #{p.id}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        type="button"
                        disabled={processorDeployBusy || processorDeployId == null}
                        onClick={() => void handleProcessorDeploy()}
                        className="rounded bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-600 disabled:opacity-50 dark:bg-emerald-800 dark:hover:bg-emerald-700"
                      >
                        {processorDeployBusy ? "…" : "Deploy here"}
                      </button>
                    </div>
                  )}
                  {processorDeployErr ? (
                    <p className="mt-2 font-mono text-xs text-red-600 dark:text-red-400">
                      {processorDeployErr}
                    </p>
                  ) : null}
                </div>

                {upgradeErr ? (
                  <p className="font-mono text-xs text-red-600 dark:text-red-400">{upgradeErr}</p>
                ) : null}

                {holding.structures.length > 0 ? (
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-ui-muted">
                      Structures
                    </p>
                    <ul className="mt-2 flex flex-col gap-2">
                      {holding.structures.map((s) => (
                        <li
                          key={s.id}
                          className="list-none rounded border border-cyan-900/40 bg-zinc-950/60 px-2 py-2 font-mono text-xs text-ui-muted"
                        >
                          <div>
                            <span className="text-zinc-800 dark:text-foreground">{s.key}</span>
                            {s.blueprintId ? ` · ${s.blueprintId}` : ""} · #{s.id} · slots {s.slotWeight}{" "}
                            · cond {s.condition}
                          </div>
                          {Object.keys(s.upgrades).length > 0 ? (
                            <div className="mt-1 text-xs text-ui-muted">
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
                                  className="rounded border border-zinc-300 bg-zinc-100 px-2 py-1 text-xs font-semibold text-zinc-800 hover:bg-zinc-200 disabled:opacity-50 dark:border-cyan-800 dark:bg-zinc-800 dark:text-foreground dark:hover:bg-zinc-700"
                                >
                                  {upgradingKey === ukey
                                    ? "…"
                                    : `${def.upgradeKey} → L${offer.nextLevel} (${offer.priceCr.toLocaleString()}cr)`}
                                </button>
                              );
                            })}
                          </div>
                        </li>
                      ))}
                    </ul>
                    <p className="mt-2 text-xs text-ui-muted">
                      In-game: <span className="font-mono">upgradeproperty</span> &lt;structure id&gt;{" "}
                      &lt;upgrade_key&gt;
                    </p>
                  </div>
                ) : null}

                {(holding.workshops?.length ?? 0) > 0 ? (
                  <div className="border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                    <p className="text-xs font-medium uppercase tracking-wide text-ui-muted">
                      Fabrication (workshops)
                    </p>
                    {workshopPanelErr ? (
                      <p className="mb-2 font-mono text-xs text-red-600 dark:text-red-400">
                        {workshopPanelErr}
                      </p>
                    ) : null}
                    <label className="mt-2 flex flex-col gap-0.5 font-mono text-xs text-ui-muted">
                      Workshop
                      <select
                        value={fabWorkshopId ?? ""}
                        onChange={(ev) => setFabWorkshopId(Number(ev.target.value))}
                        className="min-w-[12rem] rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-foreground"
                      >
                        {(holding.workshops ?? []).map((w) => (
                          <option key={w.workshopId} value={w.workshopId}>
                            {w.key} · {w.blueprintId || "—"} · #{w.workshopId}
                          </option>
                        ))}
                      </select>
                    </label>
                    {selectedFabWorkshop ? (
                      <div className="mt-2 rounded border border-cyan-900/30 bg-zinc-950/40 p-2 font-mono text-xs text-ui-muted">
                        <div>Station: {selectedFabWorkshop.stationKind}</div>
                        <div>Queue: {selectedFabWorkshop.jobQueue.length} job(s)</div>
                        <div className="mt-1">
                          Inputs:{" "}
                          {Object.keys(selectedFabWorkshop.inputInventory).length
                            ? Object.entries(selectedFabWorkshop.inputInventory)
                                .map(([k, v]) => `${k}=${v}`)
                                .join(", ")
                            : "—"}
                        </div>
                        <div>
                          Output:{" "}
                          {Object.keys(selectedFabWorkshop.outputInventory).length
                            ? Object.entries(selectedFabWorkshop.outputInventory)
                                .map(([k, v]) => `${k}=${v}`)
                                .join(", ")
                            : "—"}
                        </div>
                      </div>
                    ) : null}
                    <div className="mt-3 flex flex-col gap-2 border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                      <p className="text-xs font-semibold uppercase tracking-wide text-ui-muted">
                        Queue job
                      </p>
                      <div className="flex flex-wrap items-end gap-2">
                        <label className="flex flex-col gap-0.5 font-mono text-xs text-ui-muted">
                          Recipe
                          <select
                            value={fabRecipeKey}
                            onChange={(ev) => setFabRecipeKey(ev.target.value)}
                            className="min-w-[12rem] max-w-[20rem] rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-foreground"
                          >
                            {fabRecipeOptions.length === 0 ? (
                              <option value="">No recipes for this station</option>
                            ) : (
                              fabRecipeOptions.map((r) => (
                                <option key={r.id} value={r.id}>
                                  {r.name}
                                </option>
                              ))
                            )}
                          </select>
                        </label>
                        <label className="flex flex-col gap-0.5 font-mono text-xs text-ui-muted">
                          runs
                          <input
                            value={fabRuns}
                            onChange={(ev) => setFabRuns(ev.target.value)}
                            className="w-16 rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-foreground"
                          />
                        </label>
                        <button
                          type="button"
                          disabled={workshopQueueBusy || !fabRecipeKey}
                          onClick={() => void handleWorkshopQueue()}
                          className="rounded bg-violet-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-600 disabled:opacity-50 dark:bg-violet-800 dark:hover:bg-violet-700"
                        >
                          {workshopQueueBusy ? "…" : "Queue"}
                        </button>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-col gap-2 border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                      <p className="text-xs font-semibold uppercase tracking-wide text-ui-muted">
                        Feed refined
                      </p>
                      <div className="flex flex-wrap items-end gap-2">
                        <label className="flex flex-col gap-0.5 font-mono text-xs text-ui-muted">
                          Refined product
                          <select
                            value={fabProductKey}
                            onChange={(ev) => {
                              const pk = ev.target.value;
                              setFabProductKey(pk);
                              const row = fabFeedRows.find((r) => r.productKey === pk);
                              if (row) setFabUnits(String(row.unitsAvailable));
                            }}
                            className="min-w-[12rem] max-w-[20rem] rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-foreground"
                          >
                            {fabFeedRows.length === 0 ? (
                              <option value="">No feed stock</option>
                            ) : (
                              fabFeedRows.map((r) => (
                                <option key={r.productKey} value={r.productKey}>
                                  {r.name} ({r.unitsAvailable})
                                </option>
                              ))
                            )}
                          </select>
                        </label>
                        <label className="flex flex-col gap-0.5 font-mono text-xs text-ui-muted">
                          units
                          <input
                            type="number"
                            min={0.01}
                            max={
                              fabFeedRows.find((r) => r.productKey === fabProductKey)?.unitsAvailable ??
                              undefined
                            }
                            step={0.01}
                            value={fabUnits}
                            onChange={(ev) => setFabUnits(ev.target.value)}
                            className="w-24 rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-foreground"
                          />
                        </label>
                        <label className="flex items-center gap-2 font-mono text-xs text-ui-muted">
                          <input
                            type="checkbox"
                            checked={fabHoldingOnly}
                            onChange={(ev) => setFabHoldingOnly(ev.target.checked)}
                          />
                          Holding sources only
                        </label>
                        <button
                          type="button"
                          disabled={workshopFeedBusy || !fabProductKey || !fabUnits.trim()}
                          onClick={() => void handleWorkshopFeed()}
                          className="rounded bg-amber-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-600 disabled:opacity-50 dark:bg-amber-800 dark:hover:bg-amber-700"
                        >
                          {workshopFeedBusy ? "…" : "Feed"}
                        </button>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-col gap-2 border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                      <p className="text-xs font-semibold uppercase tracking-wide text-ui-muted">
                        Collect output
                      </p>
                      <div className="flex flex-wrap items-end gap-2">
                        <label className="flex flex-col gap-0.5 font-mono text-xs text-ui-muted">
                          Product (optional)
                          <select
                            value={fabCollectKey}
                            onChange={(ev) => setFabCollectKey(ev.target.value)}
                            className="min-w-[12rem] max-w-[20rem] rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-foreground"
                          >
                            <option value="">All</option>
                            {Object.entries(selectedFabWorkshop?.outputInventory ?? {})
                              .filter(([, v]) => Number(v) > 0)
                              .map(([k]) => {
                                const label =
                                  (holding.manufacturedProducts ?? []).find((p) => p.id === k)?.name ??
                                  k;
                                return (
                                  <option key={k} value={k}>
                                    {label}
                                  </option>
                                );
                              })}
                          </select>
                        </label>
                        <button
                          type="button"
                          disabled={workshopCollectBusy}
                          onClick={() => void handleWorkshopCollect()}
                          className="rounded bg-emerald-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 dark:bg-emerald-900 dark:hover:bg-emerald-800"
                        >
                          {workshopCollectBusy ? "…" : "Collect / sell"}
                        </button>
                      </div>
                    </div>
                    <p className="mt-2 text-xs text-ui-muted">
                      In-game: <span className="font-mono">queuefab</span>,{" "}
                      <span className="font-mono">feedfab</span>,{" "}
                      <span className="font-mono">collectfab</span>
                    </p>
                  </div>
                ) : null}

                {holding.eventQueuePreview.length > 0 ? (
                  <details className="text-xs text-ui-muted">
                    <summary className="cursor-pointer font-mono">Event preview</summary>
                    <pre className="mt-1 max-h-40 overflow-auto rounded bg-zinc-100 p-2 dark:bg-zinc-950">
                      {JSON.stringify(holding.eventQueuePreview, null, 2)}
                    </pre>
                  </details>
                ) : null}

                {(holding.buildCatalog?.length ?? 0) > 0 ? (
                  <div className="border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                    <p className="text-xs font-medium uppercase tracking-wide text-ui-muted">
                      Build (catalog)
                    </p>
                    {buildErr ? (
                      <p className="mb-2 font-mono text-xs text-red-600 dark:text-red-400">
                        {buildErr}
                      </p>
                    ) : null}
                    <div className="mt-2 flex flex-wrap items-end gap-2">
                      <label className="flex flex-col gap-0.5 font-mono text-xs text-ui-muted">
                        Blueprint
                        <select
                          value={buildBlueprintId}
                          onChange={(ev) => setBuildBlueprintId(ev.target.value)}
                          className="min-w-[12rem] rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-foreground"
                        >
                          {(holding.buildCatalog ?? []).map((row) => (
                            <option key={row.id} value={row.id}>
                              {row.name} — {row.priceCr.toLocaleString()}cr · slots {row.slotWeight}
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
                    <p className="mt-2 text-xs text-ui-muted">
                      In-game: <span className="font-mono">buildproperty</span> &lt;blueprintId&gt;
                    </p>
                  </div>
                ) : null}

                {!holding.operation.kind ? (
                  <div className="border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                    {startErr ? (
                      <p className="mb-2 font-mono text-xs text-red-600 dark:text-red-400">
                        {startErr}
                      </p>
                    ) : null}
                    {holding.allowedOperationKinds.length > 1 ? (
                      <label className="mb-2 flex flex-wrap items-center gap-2 font-mono text-xs text-ui-muted">
                        Operation kind
                        <select
                          value={opKindChoice}
                          onChange={(ev) => setOpKindChoice(ev.target.value)}
                          className="rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-foreground"
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
                    <p className="mt-2 text-xs text-ui-muted">
                      Default for this zone: {holding.defaultOperationKind ?? "—"}. In-game:{" "}
                      <span className="font-mono">startproperty</span>.
                    </p>
                  </div>
                ) : (
                  <div className="border-t border-zinc-100 pt-3 dark:border-cyan-900/40">
                    {pauseErr ? (
                      <p className="mb-2 font-mono text-xs text-red-600 dark:text-red-400">
                        {pauseErr}
                      </p>
                    ) : null}
                    {retoolErr ? (
                      <p className="mb-2 font-mono text-xs text-red-600 dark:text-red-400">
                        {retoolErr}
                      </p>
                    ) : null}
                    <button
                      type="button"
                      disabled={pauseBusy}
                      onClick={() => void handlePauseToggle(!holding.operation.paused)}
                      className="rounded border border-cyan-800/60 bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-cyber-cyan hover:bg-cyan-900/40 disabled:opacity-50"
                    >
                      {pauseBusy ? "…" : holding.operation.paused ? "Resume income" : "Pause income"}
                    </button>
                    {(() => {
                      const cur = holding.operation.kind;
                      const opts = holding.allowedOperationKinds.filter((k) => k !== cur);
                      if (opts.length === 0) {
                        return (
                          <p className="mt-2 font-mono text-xs text-ui-muted">
                            No alternate operation type for this zone. In-game:{" "}
                            <span className="font-mono">pauseproperty</span> /{" "}
                            <span className="font-mono">resumeproperty</span> /{" "}
                            <span className="font-mono">retoolproperty</span>.
                          </p>
                        );
                      }
                      return (
                        <div className="mt-3 space-y-2">
                          <label className="flex flex-wrap items-center gap-2 font-mono text-xs text-ui-muted">
                            Retool to
                            <select
                              value={retoolKind}
                              onChange={(ev) => setRetoolKind(ev.target.value)}
                              className="rounded border border-zinc-300 bg-white px-2 py-1 text-zinc-800 dark:border-cyan-800 dark:bg-zinc-900 dark:text-foreground"
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
                              : `Retool (${holding.retoolFeeCr.toLocaleString()}cr)`}
                          </button>
                          <p className="text-xs text-ui-muted">
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
              </CsPanel>

              <section id="property-deed-resale" aria-label="Property deed resale" className="scroll-mt-4">
                <CsPanel title="Property Deed Resale">
                  <PropertyDeedListForm defaultClaimId={claim.id} />
                </CsPanel>
              </section>
        </div>
      )}
    </CsPage>
  );
}
