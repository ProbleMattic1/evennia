"use client";

import { useCallback, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { ActionGrid } from "@/components/action-grid";
import { MissionBoard } from "@/components/mission-board";
import { QuestBoard } from "@/components/quest-board";
import { PanelExpandButton } from "@/components/panel-expand-button";
import { useControlSurface } from "@/components/control-surface-provider";
import type { MineRigRow, MineSiteDetails, MissionsState, PlayAction, QuestsState } from "@/lib/ui-api";
import {
  listMinePropertyForClaims,
  mineReactivate,
  mineRepairRig,
  mineUndeploy,
} from "@/lib/ui-api";
import { volumeTierStyle, rarityTierStyle } from "@/lib/mine-tier-styles";
import { compositionToLines, displayResourceName } from "@/lib/resource-display";
import { useResourceNameLookup } from "@/lib/use-resource-name-lookup";
import { useDashboardPanelOpen } from "@/lib/use-dashboard-panel-open";

type PrimaryProps = {
  site: MineSiteDetails;
};

const EMPTY_MISSIONS: MissionsState = {
  morality: { good: 0, evil: 0, lawful: 0, chaotic: 0 },
  opportunities: [],
  active: [],
  completed: [],
};

const EMPTY_QUESTS: QuestsState = {
  flags: {},
  opportunities: [],
  active: [],
  completed: [],
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

/** Like Kv, but stacks multiple lines on the right (display names + one fact per line). */
function LabeledStackLines({ label, lines }: { label: string; lines: { key: string; text: string }[] }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="shrink-0 text-ui-muted">{label}</span>
      {lines.length === 0 ? (
        <span className="min-w-0 truncate text-right font-mono text-foreground">—</span>
      ) : (
        <div className="min-w-0 space-y-0.5 text-right font-mono text-foreground">
          {lines.map((l) => (
            <div key={l.key}>{l.text}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-1">
      <div className="bg-cyan-900/30 px-1.5 py-0.5 text-xs font-bold uppercase tracking-widest text-cyber-cyan">
        {title}
      </div>
      <div className="border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-xs">
        <div className="flex flex-col gap-1 text-xs">{children}</div>
      </div>
    </section>
  );
}

/** Same expand/collapse control as dashboard `Panel` (`PanelExpandButton`). */
function MineDetailSectionCard({
  panelKey,
  title,
  children,
  uppercaseTitle = true,
}: {
  panelKey: string;
  title: string;
  children: ReactNode;
  uppercaseTitle?: boolean;
}) {
  const [open, setOpen] = useDashboardPanelOpen(panelKey, true);
  return (
    <section className="mb-1">
      <div className="flex min-w-0 items-center bg-cyan-900/30 px-1.5 py-0.5 text-xs font-bold tracking-widest">
        <span className={`min-w-0 truncate text-cyber-cyan ${uppercaseTitle ? "uppercase" : "normal-case"}`}>{title}</span>
        <PanelExpandButton
          open={open}
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="ml-auto shrink-0"
        />
      </div>
      {open ? (
        <div className="border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-xs">
          <div className="flex flex-col gap-1 text-xs">{children}</div>
        </div>
      ) : null}
    </section>
  );
}

function Kv({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="shrink-0 text-ui-muted">{label}</span>
      <span className="min-w-0 truncate text-right font-mono text-foreground">
        {value}
      </span>
    </div>
  );
}

function RigDetailRows({ r }: { r: MineRigRow }) {
  return (
    <div className="border-b border-cyan-900/40 pb-2 last:border-0">
      <p className="font-mono text-xs font-medium text-foreground">{r.key}</p>
      <div className="mt-1 space-y-0.5 pl-0">
        <Kv label="Rating" value={r.rating} />
        <Kv label="Wear" value={`${r.wear}%`} />
        <Kv label="Operational" value={r.operational ? "Yes" : "No"} />
        {r.mode != null && r.mode !== "" ? <Kv label="Mode" value={r.mode} /> : null}
        {r.powerLevel != null && r.powerLevel !== "" ? (
          <Kv label="Power" value={r.powerLevel} />
        ) : null}
        {r.targetFamily != null && r.targetFamily !== "" ? (
          <Kv label="Target" value={r.targetFamily} />
        ) : null}
        {r.purityCutoff != null && r.purityCutoff !== "" ? (
          <Kv label="Purity" value={r.purityCutoff} />
        ) : null}
        {r.maintenanceLevel != null && r.maintenanceLevel !== "" ? (
          <Kv label="Maintenance" value={r.maintenanceLevel} />
        ) : null}
        {r.needsRepair ? (
          <span className="text-xs font-medium text-amber-600 dark:text-amber-400">
            Needs repair
          </span>
        ) : null}
      </div>
    </div>
  );
}

type ReturnedEquipment = NonNullable<
  import("@/lib/ui-api").MineUndeployResult["returnedEquipment"]
>;

/** Primary mine UI: read-only core cards only (left column on Play). */
export function MineDetailsPanel({ site }: PrimaryProps) {
  const resourceNames = useResourceNameLookup();
  const compositionLines = compositionToLines(site.composition || {}, resourceNames).map((l) => ({
    key: l.key,
    text: `${l.displayName} ${l.pct}%`,
  }));
  const inventoryLines = Object.entries(site.inventory || {}).map(([k, v]) => ({
    key: k,
    text: `${displayResourceName(k, resourceNames)}: ${Number(v).toFixed(1)}t`,
  }));

  const pk = (slug: string) => `play-mine:${site.id}:${slug}`;

  return (
    <div>
      <div className="mt-1 grid auto-rows-min grid-cols-1 gap-2">
        <MineDetailSectionCard panelKey={pk("identity")} title={site.key} uppercaseTitle={false}>
          <Kv label="Site key" value={site.siteKey} />
          <Kv label="Location" value={site.location ?? site.roomKey ?? "—"} />
          <Kv label="Room" value={site.roomKey} />
        </MineDetailSectionCard>

        <MineDetailSectionCard panelKey={pk("status")} title="Status">
          <Kv label="Owner" value={site.owner ?? "Unclaimed"} />
          <Kv label="Claimed" value={site.isClaimed ? "Yes" : "No"} />
          <Kv label="Active" value={site.active ? "Yes" : "No"} />
          <Kv
            label="Mining op"
            value={
              site.mineOperationActive != null
                ? site.mineOperationActive
                  ? "Active"
                  : "Idle"
                : "—"
            }
          />
          <Kv label="Survey" value={`Level ${site.surveyLevel}`} />
        </MineDetailSectionCard>

        <MineDetailSectionCard panelKey={pk("deposit")} title="Deposit">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5">
              <span className="text-ui-muted">Volume</span>
              <span
                className={`rounded px-1.5 py-0.5 font-mono text-xs font-medium ${
                  volumeTierStyle(site.volumeTierCls).badge
                }`}
              >
                {site.volumeTier}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-ui-muted">Rarity</span>
              <span
                className={`rounded px-1.5 py-0.5 font-mono text-xs font-medium ${
                  rarityTierStyle(site.resourceRarityTierCls).badge
                }`}
              >
                {site.resourceRarityTier}
              </span>
            </div>
          </div>
          <Kv label="Richness" value={site.richness.toFixed(4)} />
          <Kv label="Output" value={`${site.baseOutputTons}t/cycle`} />
          <Kv label="Resources" value={site.resources} />
          <LabeledStackLines label="Composition" lines={compositionLines} />
        </MineDetailSectionCard>

        <MineDetailSectionCard panelKey={pk("hazard")} title="Hazard">
          <Kv label="Level" value={site.hazardLevel} />
          <Kv label="Rating" value={site.hazardLabel} />
        </MineDetailSectionCard>

        <MineDetailSectionCard panelKey={pk("licensing")} title="Licensing">
          <Kv label="License" value={`Level ${site.licenseLevel}`} />
          <Kv label="Tax" value={`${(site.taxRate * 100).toFixed(1)}%`} />
        </MineDetailSectionCard>

        <MineDetailSectionCard panelKey={pk("cycle")} title="Cycle">
          <Kv label="Last processed" value={formatDate(site.lastProcessedAt)} />
          <Kv label="Est. value" value={`${site.estimatedValuePerCycle.toLocaleString()}cr`} />
        </MineDetailSectionCard>

        <MineDetailSectionCard panelKey={pk("depletion")} title="Depletion">
          <Kv label="Rate" value={`${(site.depletionRate * 100).toFixed(2)}%`} />
          <Kv label="Floor" value={`${Math.round(site.richnessFloor * 100)}%`} />
        </MineDetailSectionCard>

        <MineDetailSectionCard panelKey={pk("storage")} title="Storage">
          <Kv label="Used" value={`${site.storageUsed} / ${site.storageCapacity}t`} />
          {inventoryLines.length > 0 ? <LabeledStackLines label="Stored" lines={inventoryLines} /> : null}
        </MineDetailSectionCard>

        {site.rig && (
          <MineDetailSectionCard panelKey={pk("rig")} title="Rig (active)">
            <Kv label="Model" value={site.rig} />
            <Kv label="Rating" value={site.rigRating ?? "—"} />
            <Kv label="Wear" value={site.rigWear != null ? `${site.rigWear}%` : "—"} />
            <Kv label="Operational" value={site.rigOperational ? "Yes" : "No"} />
            <Kv label="Mode" value={site.rigMode ?? "—"} />
            <Kv label="Power" value={site.rigPowerLevel ?? "—"} />
            <Kv label="Target" value={site.rigTargetFamily ?? "—"} />
            <Kv label="Purity" value={site.rigPurityCutoff ?? "—"} />
            <Kv label="Maintenance" value={site.rigMaintenanceLevel ?? "—"} />
          </MineDetailSectionCard>
        )}
      </div>
    </div>
  );
}

type MinePlayRightColumnProps = {
  site: MineSiteDetails;
  playActions: PlayAction[];
  onPlayReload: () => void;
};

/** Missions only — placed above Mine detail on Play. */
export function PlayMissionsPanel({ onPlayReload }: { onPlayReload: () => void }) {
  const router = useRouter();
  const { data: csData, reload: reloadControlSurface } = useControlSurface();

  const bump = useCallback(() => {
    onPlayReload();
    reloadControlSurface();
    router.refresh();
  }, [onPlayReload, reloadControlSurface, router]);

  const missions = csData?.missions ?? EMPTY_MISSIONS;

  return (
    <div className="max-h-[min(420px,55vh)] min-h-0 overflow-y-auto overflow-x-hidden pr-0.5">
      <MissionBoard missions={missions} onChanged={bump} />
    </div>
  );
}

/** Main storyline quests — same data as control surface ``quests``; Play surface only. */
export function PlayQuestsPanel({ onPlayReload }: { onPlayReload: () => void }) {
  const router = useRouter();
  const { data: csData, reload: reloadControlSurface } = useControlSurface();

  const bump = useCallback(() => {
    onPlayReload();
    reloadControlSurface();
    router.refresh();
  }, [onPlayReload, reloadControlSurface, router]);

  const quests = csData?.quests ?? EMPTY_QUESTS;

  return (
    <div className="max-h-[min(420px,55vh)] min-h-0 overflow-y-auto overflow-x-hidden pr-0.5">
      <QuestBoard quests={quests} onChanged={bump} />
    </div>
  );
}

/**
 * Right column on Play for mine rooms (inside Mine detail): actions, field service, then logs/rigs.
 */
export function MinePlayRightColumn({ site, playActions, onPlayReload }: MinePlayRightColumnProps) {
  const router = useRouter();
  const { reload: reloadControlSurface } = useControlSurface();

  const bump = useCallback(() => {
    onPlayReload();
    reloadControlSurface();
    router.refresh();
  }, [onPlayReload, reloadControlSurface, router]);

  const [undeployBusy, setUndeployBusy] = useState(false);
  const [undeployError, setUndeployError] = useState<string | null>(null);
  const [postUndeploy, setPostUndeploy] = useState<ReturnedEquipment | null>(null);

  const [listPrice, setListPrice] = useState<string>("");
  const [listBusy, setListBusy] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  const [reactivateBusy, setReactivateBusy] = useState(false);
  const [reactivateError, setReactivateError] = useState<string | null>(null);

  const [repairBusyRigKey, setRepairBusyRigKey] = useState<string | null>(null);
  const [repairError, setRepairError] = useState<string | null>(null);

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
        bump();
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
        router.push("/real-estate#claims-market");
        bump();
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
        bump();
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
    bump();
  }

  async function handleRepairRig(rigKey: string) {
    if (repairBusyRigKey) return;
    setRepairError(null);
    setRepairBusyRigKey(rigKey);
    try {
      await mineRepairRig({
        siteId: site.id,
        rigKey,
        roomKey: site.roomKey,
      });
      bump();
    } catch (err) {
      setRepairError(String(err instanceof Error ? err.message : "Repair failed."));
    } finally {
      setRepairBusyRigKey(null);
    }
  }

  const equipmentLines =
    postUndeploy != null
      ? [
          postUndeploy.rig ? `Rig: ${postUndeploy.rig.key}` : null,
          postUndeploy.storage ? `Storage: ${postUndeploy.storage.key}` : null,
          postUndeploy.hauler ? `Hauler: ${postUndeploy.hauler.key}` : null,
        ].filter(Boolean)
      : [];

  const needsFieldService = site.rigs?.some((r) => r.needsRepair);

  return (
    <div>
      <Card title="Actions">
        <ActionGrid actions={playActions} />
        {(showUndeploy || showIdleActions) && (
          <div className="mt-2 flex flex-col gap-1.5 border-t border-cyan-900/40 pt-2">
            {postUndeploy != null ? (
              <div className="space-y-2 rounded border border-emerald-800/50 bg-zinc-900/80 p-2">
                <p className="text-xs text-foreground">
                  {equipmentLines.length > 0
                    ? "Equipment returned to inventory:"
                    : "Rig, storage, and hauler (when present) returned to your inventory."}
                </p>
                {equipmentLines.length > 0 ? (
                  <ul className="list-inside list-disc font-mono text-xs text-ui-muted">
                    {equipmentLines.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                ) : null}
                <button
                  type="button"
                  onClick={handleDismissUndeployBanner}
                  className="w-fit rounded border border-cyan-800/60 bg-zinc-900 px-2 py-1 text-xs font-medium text-cyber-cyan hover:bg-cyan-900/40"
                >
                  Dismiss
                </button>
              </div>
            ) : null}

            {showUndeploy && (
              <>
                <button
                  type="button"
                  onClick={() => void handleUndeploy()}
                  disabled={undeployBusy}
                  className="w-fit rounded border border-amber-600/70 bg-zinc-900 px-2 py-1 text-xs font-medium text-amber-300 hover:bg-amber-900/20 disabled:opacity-50"
                >
                  {undeployBusy ? "Undeploying…" : "Undeploy Mine"}
                </button>
                {undeployError ? (
                  <p className="text-xs text-red-600 dark:text-red-400">{undeployError}</p>
                ) : null}
              </>
            )}

            {showIdleActions && (
              <div className="space-y-2 rounded border border-cyan-800/50 bg-zinc-900/80 p-2">
                <p className="text-xs text-foreground">
                  Mine is idle. Reactivate with your gear, or list the property on the claims market.
                </p>
                <button
                  type="button"
                  onClick={() => void handleReactivate(undefined)}
                  disabled={reactivateBusy}
                  className="w-fit rounded border border-cyan-800/60 bg-zinc-900 px-2 py-1 text-xs font-medium text-cyber-cyan hover:bg-cyan-900/40 disabled:opacity-50"
                >
                  {reactivateBusy ? "Working…" : "Reactivate (inventory gear)"}
                </button>
                {reactivateError ? (
                  <p className="text-xs text-red-600 dark:text-red-400">{reactivateError}</p>
                ) : null}
                <div className="flex flex-wrap items-center gap-2 border-t border-cyan-900/50 pt-2">
                  <label className="flex items-center gap-1.5">
                    <span className="text-xs text-ui-muted">List price (cr)</span>
                    <input
                      type="number"
                      min={0}
                      value={listPrice}
                      onChange={(e) => setListPrice(e.target.value)}
                      className="w-28 rounded border border-cyan-800/60 bg-zinc-900 px-2 py-0.5 text-xs font-mono text-foreground"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => void handleListProperty()}
                    disabled={listBusy}
                    className="rounded border border-cyan-800/60 bg-zinc-900 px-2 py-1 text-xs font-medium text-cyber-cyan hover:bg-cyan-900/40 disabled:opacity-50"
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
        )}
      </Card>

      {needsFieldService ? (
        <Card title="Field service">
          {site.rigs
            ?.filter((r) => r.needsRepair)
            .map((r) => (
              <div
                key={r.key}
                className="flex flex-col gap-1 border-b border-cyan-900/40 pb-2 last:border-0"
              >
                <span className="font-mono text-xs text-foreground">{r.key}</span>
                {r.repairTotalCr != null ? (
                  <span className="text-xs text-ui-muted">
                    Total {r.repairTotalCr.toLocaleString()}cr — service{" "}
                    {(r.repairVendorCr ?? 0).toLocaleString()}cr, tax{" "}
                    {(r.repairTaxCr ?? 0).toLocaleString()}cr (3%)
                  </span>
                ) : null}
                <button
                  type="button"
                  onClick={() => void handleRepairRig(r.key)}
                  disabled={repairBusyRigKey !== null}
                  className="w-fit rounded border border-cyan-800/60 bg-zinc-900 px-2 py-1 text-xs font-medium text-cyber-cyan hover:bg-cyan-900/40 disabled:opacity-50"
                >
                  {repairBusyRigKey === r.key ? "Repairing…" : "Pay and repair"}
                </button>
              </div>
            ))}
          {repairError ? (
            <p className="text-sm text-red-600 dark:text-red-400">{repairError}</p>
          ) : null}
        </Card>
      ) : null}

      <MineSiteSecondaryPanel site={site} />
    </div>
  );
}

/** Read-only: rigs list, cycle log, hazard log (stacked under primary controls on the right). */
export function MineSiteSecondaryPanel({ site }: { site: MineSiteDetails }) {
  return (
    <div>
      {site.rigs && site.rigs.length > 0 ? (
        <Card title="Rigs installed">
          <div className="max-h-[min(280px,45vh)] min-h-0 space-y-2 overflow-y-auto pr-0.5">
            {site.rigs.map((r) => (
              <RigDetailRows key={r.key} r={r} />
            ))}
          </div>
        </Card>
      ) : null}

      <Card title="Cycle log">
        {site.cycleLog.length > 0 ? (
          <ul className="max-h-[min(200px,35vh)] space-y-0.5 overflow-y-auto text-xs text-ui-muted">
            {site.cycleLog.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        ) : (
          <span className="text-xs text-ui-muted">—</span>
        )}
      </Card>

      <Card title="Hazard log">
        {site.hazardLog.length > 0 ? (
          <ul className="max-h-[min(200px,35vh)] space-y-0.5 overflow-y-auto text-xs text-ui-muted">
            {site.hazardLog.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        ) : (
          <span className="text-xs text-ui-muted">—</span>
        )}
      </Card>
    </div>
  );
}
