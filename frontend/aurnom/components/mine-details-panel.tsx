"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import type { MineSiteDetails } from "@/lib/ui-api";
import { listMinePropertyForClaims, mineReactivate, mineUndeploy } from "@/lib/ui-api";
import { Countdown } from "@/components/countdown";

type Props = {
  site: MineSiteDetails;
  onCycleCountdownExpired?: () => void;
};

const TIER_CLASSES: Record<string, { badge: string }> = {
  sky: {
    badge:
      "bg-sky-100 text-sky-800 ring-1 ring-sky-300 dark:bg-sky-950 dark:text-sky-400 dark:ring-sky-700/50",
  },
  emerald: {
    badge:
      "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-400 dark:ring-emerald-700/50",
  },
  amber: {
    badge:
      "bg-amber-100 text-amber-800 ring-1 ring-amber-300 dark:bg-amber-950 dark:text-amber-400 dark:ring-amber-700/50",
  },
  violet: {
    badge:
      "bg-violet-100 text-violet-800 ring-1 ring-violet-300 dark:bg-violet-950 dark:text-violet-400 dark:ring-violet-700/50",
  },
  zinc: {
    badge:
      "bg-zinc-100 text-zinc-700 ring-1 ring-zinc-300 dark:bg-zinc-900 dark:text-zinc-400 dark:ring-zinc-700/50",
  },
};

function formatDate(s: string | null) {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleString(undefined, {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return s;
  }
}

function formatComposition(comp: Record<string, number>) {
  const entries = Object.entries(comp);
  if (entries.length === 0) return "—";
  return entries.map(([k, v]) => `${k} ${Math.round(v * 100)}%`).join(", ");
}

function formatInventory(inv: Record<string, number>) {
  const entries = Object.entries(inv);
  if (entries.length === 0) return "—";
  return entries.map(([k, v]) => `${k}: ${v.toFixed(1)} t`).join(" · ");
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded border border-zinc-200 bg-zinc-50 p-2 dark:border-cyan-900/50 dark:bg-zinc-950/80">
      <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-500 dark:text-cyan-400/90">
        {title}
      </h3>
      <div className="flex flex-col gap-1 text-sm">{children}</div>
    </div>
  );
}

function Kv({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-2 text-sm">
      <span className="shrink-0 text-zinc-500 dark:text-cyan-500/80">{label}</span>
      <span className="min-w-0 truncate text-right font-mono text-zinc-800 dark:text-zinc-200">
        {value}
      </span>
    </div>
  );
}

type ReturnedEquipment = NonNullable<
  import("@/lib/ui-api").MineUndeployResult["returnedEquipment"]
>;

export function MineDetailsPanel({ site, onCycleCountdownExpired }: Props) {
  const router = useRouter();
  const [undeployBusy, setUndeployBusy] = useState(false);
  const [undeployError, setUndeployError] = useState<string | null>(null);
  const [postUndeploy, setPostUndeploy] = useState<ReturnedEquipment | null>(null);

  const [listPrice, setListPrice] = useState<string>("");
  const [listBusy, setListBusy] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  const [reactivateBusy, setReactivateBusy] = useState(false);
  const [reactivateError, setReactivateError] = useState<string | null>(null);

  const showUndeploy = site.canUndeploy;
  const showIdleActions = site.canListProperty && site.canReactivate;

  async function handleUndeploy() {
    if (!site.canUndeploy || undeployBusy) return;
    setUndeployError(null);
    setPostUndeploy(null);
    setUndeployBusy(true);
    try {
      const res = await mineUndeploy({ siteId: site.id });
      if (res.ok) {
        setPostUndeploy(res.returnedEquipment ?? ({} as ReturnedEquipment));
        setListPrice(String(site.estimatedValuePerCycle || 0));
        router.refresh();
      } else {
        setUndeployError(res.message ?? "Undeploy failed.");
      }
    } catch (err) {
      setUndeployError(String(err instanceof Error ? err.message : "Undeploy failed."));
    } finally {
      setUndeployBusy(false);
    }
  }

  async function handleListProperty() {
    if (listBusy) return;
    const price = parseInt(listPrice, 10);
    if (isNaN(price) || price < 0) {
      setListError("Enter a valid non-negative price.");
      return;
    }
    setListError(null);
    setListBusy(true);
    try {
      const res = await listMinePropertyForClaims({ siteId: site.id, price });
      if (res.ok) {
        setPostUndeploy(null);
        router.push("/claims-market");
        router.refresh();
      } else {
        setListError(res.message ?? "Failed to list property.");
      }
    } catch (err) {
      setListError(String(err instanceof Error ? err.message : "Failed to list property."));
    } finally {
      setListBusy(false);
    }
  }

  async function handleReactivate(packageId?: number) {
    if (reactivateBusy) return;
    setReactivateError(null);
    setReactivateBusy(true);
    try {
      const res = await mineReactivate({ siteId: site.id, packageId });
      if (res.ok) {
        setPostUndeploy(null);
        router.refresh();
      } else {
        setReactivateError(res.message ?? "Reactivate failed.");
      }
    } catch (err) {
      setReactivateError(String(err instanceof Error ? err.message : "Reactivate failed."));
    } finally {
      setReactivateBusy(false);
    }
  }

  function handleDismissUndeployBanner() {
    setPostUndeploy(null);
    router.refresh();
  }

  const equipmentLines =
    postUndeploy != null
      ? [
          postUndeploy.rig ? `Rig: ${postUndeploy.rig.key}` : null,
          postUndeploy.storage ? `Storage: ${postUndeploy.storage.key}` : null,
          postUndeploy.hauler ? `Hauler: ${postUndeploy.hauler.key}` : null,
        ].filter(Boolean)
      : [];

  return (
    <section className="border-b border-zinc-100 px-2 py-2 dark:border-cyan-900/30">
      <h2 className="section-label">Mine Details</h2>
      {(showUndeploy || showIdleActions) && (
        <div className="mt-1">
          <Card title="Actions">
            <div className="flex flex-col gap-1.5">
              {postUndeploy != null ? (
                <div className="space-y-2 rounded border border-emerald-200 bg-emerald-50/50 p-2 dark:border-emerald-800/50 dark:bg-emerald-950/30">
                  <p className="text-sm text-zinc-700 dark:text-zinc-300">
                    {equipmentLines.length > 0
                      ? "Equipment returned to inventory:"
                      : "Rig, storage, and hauler (when present) returned to your inventory."}
                  </p>
                  {equipmentLines.length > 0 ? (
                    <ul className="list-inside list-disc font-mono text-[12px] text-zinc-600 dark:text-zinc-400">
                      {equipmentLines.map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                  ) : null}
                  <button
                    type="button"
                    onClick={handleDismissUndeployBanner}
                    className="w-fit rounded border border-zinc-400 bg-zinc-100 px-2 py-1 text-sm font-medium text-zinc-700 hover:bg-zinc-200 dark:border-cyan-700/50 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
                  >
                    Dismiss
                  </button>
                </div>
              ) : null}

              {showUndeploy && (
                <>
                  <button
                    type="button"
                    onClick={handleUndeploy}
                    disabled={undeployBusy}
                    className="w-fit rounded border border-amber-600 bg-amber-50 px-2 py-1 text-sm font-medium text-amber-800 hover:bg-amber-100 disabled:opacity-50 dark:border-amber-500 dark:bg-amber-950/40 dark:text-amber-300 dark:hover:bg-amber-900/50"
                  >
                    {undeployBusy ? "Undeploying…" : "Undeploy Mine"}
                  </button>
                  {undeployError ? (
                    <p className="text-xs text-red-600 dark:text-red-400">{undeployError}</p>
                  ) : null}
                </>
              )}

              {showIdleActions && (
                <div className="space-y-2 rounded border border-sky-200 bg-sky-50/50 p-2 dark:border-sky-800/50 dark:bg-sky-950/30">
                  <p className="text-sm text-zinc-700 dark:text-zinc-300">
                    Mine is idle. Reactivate with your gear, or list the property on the claims market.
                  </p>
                  <button
                    type="button"
                    onClick={() => handleReactivate(undefined)}
                    disabled={reactivateBusy}
                    className="w-fit rounded border border-sky-600 bg-sky-50 px-2 py-1 text-sm font-medium text-sky-900 hover:bg-sky-100 disabled:opacity-50 dark:border-sky-500 dark:bg-sky-950/40 dark:text-sky-200 dark:hover:bg-sky-900/50"
                  >
                    {reactivateBusy ? "Working…" : "Reactivate (inventory gear)"}
                  </button>
                  {reactivateError ? (
                    <p className="text-xs text-red-600 dark:text-red-400">{reactivateError}</p>
                  ) : null}
                  <div className="flex flex-wrap items-center gap-2 border-t border-sky-200 pt-2 dark:border-sky-800/50">
                    <label className="flex items-center gap-1.5">
                      <span className="text-[12px] text-zinc-500 dark:text-cyan-500/80">List price (cr)</span>
                      <input
                        type="number"
                        min={0}
                        value={listPrice}
                        onChange={(e) => setListPrice(e.target.value)}
                        className="w-28 rounded border border-zinc-300 px-2 py-0.5 text-sm font-mono dark:border-cyan-700/50 dark:bg-zinc-900 dark:text-zinc-200"
                      />
                    </label>
                    <button
                      type="button"
                      onClick={handleListProperty}
                      disabled={listBusy}
                      className="rounded border border-emerald-600 bg-emerald-50 px-2 py-1 text-sm font-medium text-emerald-800 hover:bg-emerald-100 disabled:opacity-50 dark:border-emerald-500 dark:bg-emerald-950/40 dark:text-emerald-300 dark:hover:bg-emerald-900/50"
                    >
                      {listBusy ? "Listing…" : "List property on claims market"}
                    </button>
                  </div>
                  {listError ? (
                    <p className="text-xs text-red-600 dark:text-red-400">{listError}</p>
                  ) : null}
                </div>
              )}
            </div>
          </Card>
        </div>
      )}
      <div className="mt-1 grid auto-rows-min grid-cols-1 gap-2 sm:grid-cols-2">
        <Card title="Identity">
          <Kv label="Deposit" value={site.key} />
          <Kv label="Location" value={site.location ?? site.roomKey ?? "—"} />
          <Kv label="Room" value={site.roomKey} />
        </Card>

        <Card title="Status">
          <Kv label="Owner" value={site.owner ?? "Unclaimed"} />
          <Kv label="Active" value={site.active ? "Yes" : "No"} />
          <Kv label="Survey" value={`Level ${site.surveyLevel}`} />
        </Card>

        <Card title="Deposit">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-500 dark:text-cyan-500/80">Volume</span>
              <span
                className={`rounded px-1.5 py-0.5 font-mono text-[12px] font-medium ${
                  TIER_CLASSES[site.volumeTierCls]?.badge ?? TIER_CLASSES.zinc.badge
                }`}
              >
                {site.volumeTier}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-zinc-500 dark:text-cyan-500/80">Rarity</span>
              <span
                className={`rounded px-1.5 py-0.5 font-mono text-[12px] font-medium ${
                  TIER_CLASSES[site.resourceRarityTierCls]?.badge ?? TIER_CLASSES.zinc.badge
                }`}
              >
                {site.resourceRarityTier}
              </span>
            </div>
          </div>
          <Kv label="Output" value={`${site.baseOutputTons} t/cycle`} />
          <Kv label="Resources" value={site.resources} />
          <Kv label="Composition" value={formatComposition(site.composition)} />
        </Card>

        <Card title="Hazard">
          <Kv label="Level" value={site.hazardLevel} />
          <Kv label="Rating" value={site.hazardLabel} />
        </Card>

        <Card title="Licensing">
          <Kv label="License" value={`Level ${site.licenseLevel}`} />
          <Kv label="Tax" value={`${(site.taxRate * 100).toFixed(1)}%`} />
        </Card>

        <Card title="Cycle">
          <Kv
            label="Next cycle"
            value={
              site.nextCycleAt ? (
                <span className="flex flex-col items-end gap-0.5">
                  <span>{formatDate(site.nextCycleAt)}</span>
                  <Countdown
                    targetIso={site.nextCycleAt}
                    prefix=""
                    className="text-[11px] text-amber-600 dark:text-amber-400"
                    onExpired={onCycleCountdownExpired}
                  />
                </span>
              ) : "—"
            }
          />
          <Kv label="Last processed" value={formatDate(site.lastProcessedAt)} />
          <Kv label="Est. value" value={`${site.estimatedValuePerCycle.toLocaleString()} cr`} />
        </Card>

        <Card title="Depletion">
          <Kv label="Rate" value={`${(site.depletionRate * 100).toFixed(2)}%`} />
          <Kv label="Floor" value={`${Math.round(site.richnessFloor * 100)}%`} />
        </Card>

        <Card title="Storage">
          <Kv label="Used" value={`${site.storageUsed} / ${site.storageCapacity} t`} />
          {Object.keys(site.inventory).length > 0 && (
            <Kv label="Stored" value={formatInventory(site.inventory)} />
          )}
        </Card>

        {site.rig && (
          <Card title="Rig">
            <Kv label="Model" value={site.rig} />
            <Kv label="Rating" value={site.rigRating ?? "—"} />
            <Kv label="Wear" value={site.rigWear != null ? `${site.rigWear}%` : "—"} />
            <Kv label="Operational" value={site.rigOperational ? "Yes" : "No"} />
            <Kv label="Mode" value={site.rigMode ?? "—"} />
          </Card>
        )}

        <Card title="Cycle log">
          {site.cycleLog.length > 0 ? (
            <ul className="space-y-0.5 text-xs text-zinc-600 dark:text-cyan-500/80">
              {site.cycleLog.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          ) : (
            <span className="text-xs text-zinc-500 dark:text-cyan-500/60">—</span>
          )}
        </Card>

        <Card title="Hazard log">
          {site.hazardLog.length > 0 ? (
            <ul className="space-y-0.5 text-xs text-zinc-600 dark:text-cyan-500/80">
              {site.hazardLog.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          ) : (
            <span className="text-xs text-zinc-500 dark:text-cyan-500/60">—</span>
          )}
        </Card>
      </div>
    </section>
  );
}
