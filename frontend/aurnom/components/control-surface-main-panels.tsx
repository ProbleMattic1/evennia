"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { Countdown } from "@/components/countdown";
import { ChallengesPanel } from "@/components/challenges-panel";
import { PanelExpandButton } from "@/components/panel-expand-button";
import { DashboardMissionsPanel, EMPTY_MISSIONS } from "@/components/dashboard-missions-panel";
import { LocationBanner } from "@/components/location-banner";
import type {
  ControlSurfaceState,
  CsInventory,
  PersonalStorageBuckets,
  PersonalStorageEntry,
} from "@/lib/control-surface-api";
import type {
  DashboardAlert,
  DashboardGroupedAlerts,
  DashboardMine,
  DashboardProperty,
  DashboardShip,
  MarketCommodity,
} from "@/lib/ui-api";
import {
  claimChallengeReward,
  claimChallengeRewardsAll,
  claimChallengeRewardsForCadence,
  dashboardAckAlert,
  dashboardAckAllAlerts,
  EMPTY_ROOM_AMBIENT,
  mineDeploy,
  mineRepairRig,
} from "@/lib/ui-api";
import { formatCr as cr } from "@/lib/format-units";
import { compositionToLines, buildResourceNameLookup, displayResourceName } from "@/lib/resource-display";
import { useDashboardPanelOpen } from "@/lib/use-dashboard-panel-open";
import { useMsgStream } from "@/lib/use-msg-stream";
import { useResourceNameLookup } from "@/lib/use-resource-name-lookup";

function Panel({
  panelKey,
  title,
  children,
  className = "",
  headerActions,
}: {
  panelKey: string;
  title: string;
  children: ReactNode;
  className?: string;
  /** Rendered in the header bar, immediately left of the expand/collapse control. */
  headerActions?: ReactNode;
}) {
  const [open, setOpen] = useDashboardPanelOpen(panelKey, true);

  return (
    <section className={`mb-1 ${className}`}>
      <div className="flex min-w-0 items-center gap-1 bg-cyan-900/30 px-1.5 py-0.5 text-xs font-bold uppercase tracking-widest">
        <span className="min-w-0 truncate text-cyber-cyan">{title}</span>
        <div className="ml-auto flex shrink-0 items-center gap-1 normal-case tracking-normal">
          {headerActions}
          <PanelExpandButton
            open={open}
            onClick={() => setOpen((v) => !v)}
            aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          />
        </div>
      </div>
      {open ? <div className="border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-xs">{children}</div> : null}
    </section>
  );
}

function Kv({ k, v, dim }: { k: string; v: ReactNode; dim?: boolean }) {
  return (
    <div className="flex min-w-0 gap-1">
      <span className="shrink-0 text-ui-muted">{k}</span>
      <span className={`min-w-0 truncate font-mono ${dim ? "text-ui-muted" : "text-foreground"}`}>{v}</span>
    </div>
  );
}

function Row({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`flex min-w-0 items-baseline gap-2 ${className}`}>{children}</div>;
}

function TinyLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="shrink-0 rounded border border-cyan-800/60 px-1 py-0 text-xs text-cyber-cyan hover:bg-cyan-900/40"
    >
      {children}
    </Link>
  );
}

function TinyButton({
  onClick,
  disabled,
  children,
  danger,
}: {
  onClick: () => void;
  disabled?: boolean;
  children: ReactNode;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`shrink-0 rounded border px-1 py-0 text-xs disabled:opacity-40 ${
        danger
          ? "border-red-800/60 text-red-400 hover:bg-red-900/40"
          : "border-cyan-800/60 text-cyber-cyan hover:bg-cyan-900/40"
      }`}
    >
      {children}
    </button>
  );
}

function Badge({ label, cls }: { label: string; cls?: string }) {
  const base = "inline-block rounded px-1 text-ui-caption font-bold uppercase";
  if (cls === "rare" || cls === "epic") {
    return <span className={`${base} bg-purple-900/60 text-purple-300`}>{label}</span>;
  }
  if (cls === "uncommon") {
    return <span className={`${base} bg-green-900/60 text-green-300`}>{label}</span>;
  }
  if (cls === "common") {
    return <span className={`${base} bg-zinc-700/60 text-ui-muted`}>{label}</span>;
  }
  return <span className={`${base} bg-zinc-700/60 text-ui-muted`}>{label}</span>;
}

/** Sum `estimatedValuePerCycle` where present (matches per-row yield display). */
function resourcesCreditsRollup(items: DashboardMine[]): { sum: number; counted: number } | null {
  let sum = 0;
  let counted = 0;
  for (const m of items) {
    const v = m.estimatedValuePerCycle;
    if (typeof v === "number" && !Number.isNaN(v)) {
      sum += v;
      counted += 1;
    }
  }
  if (counted === 0) return null;
  return { sum, counted };
}

function ResourcesCreditsRollupLabel({
  items,
  className = "",
}: {
  items: DashboardMine[];
  className?: string;
}) {
  const rollup = resourcesCreditsRollup(items);
  if (!rollup) return null;
  const complete = rollup.counted === items.length;
  return (
    <span
      className={`shrink-0 font-mono text-ui-caption font-normal normal-case tracking-normal text-ui-muted ${className}`}
      title={
        complete
          ? "Credits per cycle (sum of site yields)"
          : `Credits per cycle from ${rollup.counted} of ${items.length} sites (others omit yield)`
      }
    >
      {rollup.sum.toLocaleString()}cr<span className="text-ui-soft">/cyc</span>
      {!complete ? <span className="text-ui-muted"> *</span> : null}
    </span>
  );
}

/** Same typography as `ResourcesCreditsRollupLabel` — for personal storage section bars. */
const RESOURCE_ROLLUP_MONO =
  "shrink-0 font-mono text-ui-caption font-normal normal-case tracking-normal text-ui-muted";

function PropertiesCreditsRollupLabel({
  sumCr,
  counted,
  rowCount,
}: {
  sumCr: number;
  counted: number;
  rowCount: number;
}) {
  if (counted === 0) return null;
  const complete = counted === rowCount;
  return (
    <span
      className={RESOURCE_ROLLUP_MONO}
      title={
        complete
          ? "Reference list value (sum of properties)"
          : `Reference list value from ${counted} of ${rowCount} properties (others omit list price)`
      }
    >
      {cr(sumCr)}
      {!complete ? <span className="text-ui-muted"> *</span> : null}
    </span>
  );
}

function PersonalStorageTonsRollupLabel({ tons }: { tons: number }) {
  return (
    <span className={RESOURCE_ROLLUP_MONO} title="Total stored mass">
      {tons.toLocaleString(undefined, { maximumFractionDigits: 2 })}
      <span className="text-ui-soft">t</span>
    </span>
  );
}

function PersonalStorageCreditsRollupLabel({
  sumCr,
  counted,
  rowCount,
}: {
  sumCr: number;
  counted: number;
  rowCount: number;
}) {
  if (counted === 0) return null;
  const complete = counted === rowCount;
  return (
    <span
      className={RESOURCE_ROLLUP_MONO}
      title={
        complete
          ? "Estimated value at local bids (sum of rows)"
          : `Estimated value from ${counted} of ${rowCount} rows (others omit estimate)`
      }
    >
      {cr(sumCr)}
      {!complete ? <span className="text-ui-muted"> *</span> : null}
    </span>
  );
}

function inventoryBucket(inv: CsInventory, id: string) {
  return inv.byBucket[id] ?? [];
}

function formatClaimOptionLabel(c: {
  key: string;
  id: number;
  claimSpecs?: {
    volumeTier?: string;
    resourceRarityTier?: string;
  };
}) {
  const keyText = String(c.key || "");
  const idSuffix = `#${c.id}`;
  const base = keyText.includes(idSuffix) ? keyText : `${keyText} ${idSuffix}`;
  const parts: string[] = [];
  if (c.claimSpecs?.volumeTier) parts.push(c.claimSpecs.volumeTier);
  if (c.claimSpecs?.resourceRarityTier) parts.push(c.claimSpecs.resourceRarityTier);
  return parts.length ? `${base} (${parts.join(" / ")})` : base;
}

/** Not listed in Inventory panel; Mine Operations still reads these buckets from the same payload. */
const INVENTORY_PANEL_HIDDEN_BUCKETS = new Set(["mining_claim", "property_deed"]);

/** Alerts only: original taller viewport (~10 rows), remainder scrolls. */
const ALERTS_SCROLL_LIST_CLASS =
  "max-h-[min(220px,40vh)] min-h-[48px] overflow-y-auto overflow-x-hidden pr-0.5 [scrollbar-gutter:stable]";

/** Properties, claims, personal storage: shorter viewport (~6 rows). */
const DASHBOARD_SCROLL_LIST_CLASS =
  "max-h-[min(132px,24vh)] min-h-[32px] overflow-y-auto overflow-x-hidden pr-0.5 [scrollbar-gutter:stable]";

function formatAlertAge(iso: string, nowMs: number): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "—";
  const sec = Math.max(0, Math.floor((nowMs - t) / 1000));
  if (sec < 45) return "now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 48) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
}

function AlertsPanel({
  grouped,
  onAck,
  onAckAll,
  busy,
}: {
  grouped: DashboardGroupedAlerts;
  onAck: (id: string) => void;
  onAckAll: () => void;
  busy?: boolean;
}) {
  const [nowMs, setNowMs] = useState(0);

  useEffect(() => {
    queueMicrotask(() => setNowMs(Date.now()));
    const id = window.setInterval(() => setNowMs(Date.now()), 30_000);
    return () => window.clearInterval(id);
  }, []);

  const all = [...grouped.critical, ...grouped.warning, ...grouped.info];
  if (all.length === 0) return null;

  const sevColor = (s: string) => {
    if (s === "critical") return "text-red-400";
    if (s === "warning") return "text-yellow-400";
    return "text-ui-muted";
  };

  return (
    <Panel
      panelKey="alerts"
      title={`Alerts (${all.length})`}
      headerActions={
        <TinyButton onClick={onAckAll} disabled={busy}>
          Clear all
        </TinyButton>
      }
    >
      <div className={ALERTS_SCROLL_LIST_CLASS}>
        {all.map((a: DashboardAlert) => (
          <Row key={a.id} className="mb-0.5 items-start">
            <span className={`shrink-0 text-ui-caption font-bold uppercase ${sevColor(a.severity)}`}>
              {a.severity[0].toUpperCase()}
            </span>
            <span className="min-w-0 flex-1 text-foreground">{a.title}</span>
            <span
              className="shrink-0 tabular-nums text-ui-caption text-ui-muted"
              title={a.createdAt ? new Date(a.createdAt).toLocaleString() : undefined}
            >
              {nowMs > 0 ? formatAlertAge(a.createdAt ?? "", nowMs) : "—"}
            </span>
            <TinyButton onClick={() => onAck(a.id)}>×</TinyButton>
          </Row>
        ))}
      </div>
    </Panel>
  );
}

function InventoryPanel({ inventory }: { inventory: CsInventory }) {
  const visibleOrder = (
    inventory.bucketOrder.length > 0 ? inventory.bucketOrder : Object.keys(inventory.byBucket).sort()
  ).filter((id) => !INVENTORY_PANEL_HIDDEN_BUCKETS.has(id));

  const total = visibleOrder.reduce((sum, bucketId) => {
    const rows = inventory.byBucket[bucketId];
    return sum + (rows?.length ?? 0);
  }, 0);

  if (total === 0) return null;

  const labels = inventory.bucketLabels;

  return (
    <Panel panelKey="inventory" title={`Inventory (${total})`}>
      {visibleOrder.map((bucketId) => {
        const rows = inventory.byBucket[bucketId];
        if (!rows?.length) return null;
        const title = labels[bucketId] ?? bucketId.replace(/_/g, " ");
        return (
          <div key={bucketId} className="mt-0.5 first:mt-0">
            <div className="text-xs uppercase text-ui-muted">{title}</div>
            {rows.map((item) => (
              <Row key={`${bucketId}-${item.stacked && item.ids?.length ? item.ids.join("-") : item.id}-${item.key}`}>
                <span className="flex-1 truncate text-foreground">
                  {item.count && item.count > 1 ? `${item.count}× ` : ""}
                  {item.key}
                </span>
                {bucketId === "mining_package" && item.estimatedValue != null ? (
                  <span className="font-mono text-ui-muted">{cr(item.estimatedValue)}</span>
                ) : null}
              </Row>
            ))}
          </div>
        );
      })}
    </Panel>
  );
}

function MineDeploymentPanel({
  inventory,
  onDeploy,
  busy,
}: {
  inventory: CsInventory;
  onDeploy: (packageId: number, claimId: number) => void;
  busy: boolean;
}) {
  const packageRows = inventoryBucket(inventory, "mining_package").flatMap((item) => {
    const ids = item.stacked && item.ids?.length ? item.ids : [item.id];
    return ids.map((id) => ({ ...item, id }));
  });
  const claimRows = inventoryBucket(inventory, "mining_claim").flatMap((item) => {
    const ids = item.stacked && item.ids?.length ? item.ids : [item.id];
    return ids.map((id) => ({ ...item, id }));
  });

  const [packageId, setPackageId] = useState<number | "">("");
  const [claimId, setClaimId] = useState<number | "">("");

  // Only show when deploy is possible: at least one package and one mining claim.
  if (packageRows.length === 0 || claimRows.length === 0) {
    return null;
  }

  const canDeploy = typeof packageId === "number" && typeof claimId === "number";

  return (
    <Panel panelKey="mine-operations" title="Mine Operations">
      <div className="space-y-1">
        <Kv k="packages" v={packageRows.length} />
        <Kv k="claims" v={claimRows.length} />
      </div>
      <>
          <label className="mt-1 block text-xs uppercase tracking-wide text-ui-muted">Package</label>
          <select
            className="w-full rounded border border-cyan-900/50 bg-zinc-900 px-1 py-0.5 text-xs text-foreground"
            value={packageId}
            onChange={(e) => setPackageId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Select package</option>
            {packageRows.map((p) => (
              <option key={`package-${p.id}`} value={p.id}>
                {p.key} #{p.id}
              </option>
            ))}
          </select>

          <label className="mt-1 block text-xs uppercase tracking-wide text-ui-muted">Claim</label>
          <select
            className="w-full rounded border border-cyan-900/50 bg-zinc-900 px-1 py-0.5 text-xs text-foreground"
            value={claimId}
            onChange={(e) => setClaimId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Select claim</option>
            {claimRows.map((c) => (
              <option key={`claim-${c.id}`} value={c.id}>
                {formatClaimOptionLabel(c)}
              </option>
            ))}
          </select>

          <div className="mt-1 flex items-center gap-1">
            <TinyButton onClick={() => canDeploy && onDeploy(packageId, claimId)} disabled={!canDeploy || busy}>
              Deploy mine
            </TinyButton>
            {typeof claimId === "number" ? <TinyLink href={`/claims/${claimId}`}>Claim detail →</TinyLink> : null}
          </div>
      </>
    </Panel>
  );
}

function shipClassKey(s: DashboardShip): string {
  const slug = (s.vehicleClassSlug || "").trim();
  if (slug) return slug;
  return "unknown";
}

function shipSectionLabel(s: DashboardShip): string {
  const label = (s.vehicleClassLabel || "").trim();
  if (label) return label;
  return "Other";
}

function ShipsClassGroup({
  classKey,
  label,
  items,
}: {
  classKey: string;
  label: string;
  items: DashboardShip[];
}) {
  const title = `${label} (${items.length})`;
  const [open, setOpen] = useDashboardPanelOpen(`ships:${classKey}`, true);

  return (
    <div className="mb-1 last:mb-0">
      <div className="flex min-w-0 items-center gap-1 bg-cyan-900/20 px-1 py-0.5 text-ui-caption font-bold uppercase tracking-widest">
        <span className="min-w-0 flex-1 truncate text-cyber-cyan">{title}</span>
        <PanelExpandButton
          open={open}
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="shrink-0"
        />
      </div>
      {open ? (
        <div className="pt-0.5">
          {items.map((s) => (
            <Row key={s.id}>
              <span className="flex-1 truncate font-semibold text-foreground">
                {s.count && s.count > 1 ? `${s.count}× ` : ""}
                {s.key}
              </span>
              {s.state ? <span className="text-xs text-ui-muted">{s.state}</span> : null}
              {s.location ? <span className="text-xs text-ui-muted">{s.location}</span> : null}
            </Row>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ShipsPanel({ ships }: { ships: DashboardShip[] }) {
  if (ships.length === 0) return null;

  const byClass = new Map<string, DashboardShip[]>();
  for (const s of ships) {
    const k = shipClassKey(s);
    if (!byClass.has(k)) byClass.set(k, []);
    byClass.get(k)!.push(s);
  }
  for (const list of byClass.values()) {
    list.sort((a, b) => a.key.localeCompare(b.key));
  }
  const orderedClassKeys = [...byClass.keys()].sort((a, b) => {
    const la = shipSectionLabel(byClass.get(a)![0]);
    const lb = shipSectionLabel(byClass.get(b)![0]);
    return la.localeCompare(lb);
  });

  return (
    <Panel panelKey="ships" title={`Ships (${ships.length})`}>
      {orderedClassKeys.map((classKey) => (
        <ShipsClassGroup
          key={classKey}
          classKey={classKey}
          label={shipSectionLabel(byClass.get(classKey)![0])}
          items={byClass.get(classKey) ?? []}
        />
      ))}
    </Panel>
  );
}

const RESOURCE_SITE_KIND_ORDER = ["mining_site", "flora_site", "fauna_site"] as const;

function resourceSiteKindKey(m: DashboardMine): string {
  if (m.kind && String(m.kind).length > 0) return String(m.kind);
  if (m.siteKind === "flora") return "flora_site";
  if (m.siteKind === "fauna") return "fauna_site";
  return "mining_site";
}

function resourceCategoryTitle(kindKey: string): string {
  if (kindKey === "mining_site") return "Mines";
  if (kindKey === "flora_site") return "Flora harvesters";
  if (kindKey === "fauna_site") return "Fauna harvesters";
  return kindKey
    .split("_")
    .map((w) => (w ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase() : w))
    .join(" ");
}

function visitProductionSiteLabel(m: DashboardMine): string {
  if (m.kind === "flora_site" || m.siteKind === "flora") return "Visit stand →";
  if (m.kind === "fauna_site" || m.siteKind === "fauna") return "Visit range →";
  return "Visit mine →";
}

function MineDashboardRow({
  m,
  resourceNames,
  onRepairRig,
}: {
  m: DashboardMine;
  resourceNames: ReturnType<typeof buildResourceNameLookup>;
  onRepairRig: (siteId: number) => void;
}) {
  const composition = m.composition || {};
  const hasProduces = Object.keys(composition).length > 0;
  const produceLines = hasProduces ? compositionToLines(composition, resourceNames) : [];
  const rowPanelKey = `resource-row:${encodeURIComponent(m.key)}`;
  const [open, setOpen] = useDashboardPanelOpen(rowPanelKey, true);

  return (
    <div className="mb-1 border-b border-zinc-800/60 pb-1 last:border-0 last:pb-0">
      <div className="flex min-w-0 items-start gap-1">
        <span className={`shrink-0 font-semibold ${m.active ? "text-green-400" : "text-ui-muted"}`}>
          {m.active ? "●" : "○"}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center gap-1">
            <span className="min-w-0 flex-1 truncate font-mono text-foreground">{m.key}</span>
            {m.rigWear != null && m.rigWear >= 70 ? (
              <button
                type="button"
                onClick={() => onRepairRig(m.id)}
                className="shrink-0 font-mono text-xs text-amber-400 hover:text-amber-300"
              >
                Repair rig ⚠
              </button>
            ) : null}
            {m.location ? (
              <span className="inline-flex translate-y-px">
                <TinyLink href={`/play?room=${encodeURIComponent(m.location)}`}>{visitProductionSiteLabel(m)}</TinyLink>
              </span>
            ) : null}
            <PanelExpandButton
              open={open}
              onClick={() => setOpen((v) => !v)}
              aria-label={`${open ? "Collapse" : "Expand"} ${m.key}`}
              className="shrink-0"
            />
          </div>
          {m.volumeTier ? (
            <div className="mt-0.5 flex min-w-0 items-center gap-1.5">
              <Row>
                <Badge label={m.volumeTier} cls={m.volumeTierCls} />
                <Badge label={m.resourceRarityTier ?? ""} cls={m.resourceRarityTierCls} />
              </Row>
              {m.estimatedValuePerCycle != null ? (
                <span className="shrink-0 font-mono text-xs text-ui-muted">
                  {cr(m.estimatedValuePerCycle)} <span className="text-ui-soft">yld</span>
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
      {open ? (
        <div className={`ml-3 mt-1 items-start gap-x-2 ${hasProduces ? "grid grid-cols-2" : ""}`}>
          <div className="min-w-0 space-y-0">
            <Kv k="storage" v={`${m.storageUsed}/${m.storageCapacity}t`} />
            {m.rigWear != null ? <Kv k="rig wear" v={`${m.rigWear}%${!m.rigOperational ? " ⚠ offline" : ""}`} /> : null}
            {Object.keys(m.inventory || {}).length > 0 ? (
              <Kv
                k="stored"
                v={Object.entries(m.inventory || {})
                  .map(([k, v]) => `${displayResourceName(k, resourceNames)}: ${v.toFixed(1)}t`)
                  .join(" · ")}
              />
            ) : null}
          </div>
          {hasProduces ? (
            <div className="min-w-0 border-l border-zinc-800/60 pl-2">
              <div className="flex min-w-0 flex-col gap-0.5">
                <span className="shrink-0 font-mono text-ui-muted">produces</span>
                <div className="flex min-w-0 flex-col gap-0.5">
                  {produceLines.map((line) => (
                    <span key={line.key} className="font-mono text-foreground">
                      {line.displayName} {line.pct}%
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function ResourcesCategoryGroup({
  kindKey,
  items,
  resourceNames,
  onRepairRig,
}: {
  kindKey: string;
  items: DashboardMine[];
  resourceNames: ReturnType<typeof buildResourceNameLookup>;
  onRepairRig: (siteId: number) => void;
}) {
  const title = `${resourceCategoryTitle(kindKey)} (${items.length})`;
  const [open, setOpen] = useDashboardPanelOpen(`resources:${kindKey}`, true);
  const allActive = items.every((m) => m.active);

  return (
    <div className="mb-1 last:mb-0">
      <div className="flex min-w-0 items-center gap-1 bg-cyan-900/20 px-1 py-0.5 text-ui-caption font-bold uppercase tracking-widest">
        {!open ? (
          <span
            className={`shrink-0 font-semibold ${allActive ? "text-green-400" : "text-red-400"}`}
            title={allActive ? "All sites in this category active" : "At least one site inactive"}
            aria-hidden
          >
            ●
          </span>
        ) : null}
        <span className="min-w-0 flex-1 truncate text-cyber-cyan">{title}</span>
        <ResourcesCreditsRollupLabel items={items} />
        <PanelExpandButton
          open={open}
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="shrink-0"
        />
      </div>
      {open ? (
        <div className="pt-0.5">
          {items.map((m) => (
            <MineDashboardRow key={m.key} m={m} resourceNames={resourceNames} onRepairRig={onRepairRig} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ResourcesPanel({
  resources,
  market,
  miningNextCycleAt,
  mineStorageValueCr,
  onReload,
  onRepairRig,
}: {
  resources: DashboardMine[];
  market: MarketCommodity[];
  miningNextCycleAt: string;
  /** Total estimated cr held at production sites (same as Character “mine storage”). */
  mineStorageValueCr: number;
  onReload: () => void;
  onRepairRig: (siteId: number) => void;
}) {
  const resourceNames = useMemo(() => buildResourceNameLookup(market), [market]);
  const [open, setOpen] = useDashboardPanelOpen("resources", true);
  const allActive = resources.every((m) => m.active);
  const nextAt =
    [miningNextCycleAt, resources.find((m) => m.nextCycleAt)?.nextCycleAt].find((s) => s && String(s).length > 0) ??
    null;

  if (resources.length === 0) return null;

  const byKind = new Map<string, DashboardMine[]>();
  for (const m of resources) {
    const k = resourceSiteKindKey(m);
    if (!byKind.has(k)) byKind.set(k, []);
    byKind.get(k)!.push(m);
  }
  for (const list of byKind.values()) {
    list.sort((a, b) => a.key.localeCompare(b.key));
  }
  const orderedKindKeys = [
    ...RESOURCE_SITE_KIND_ORDER.filter((k) => (byKind.get(k)?.length ?? 0) > 0),
    ...[...byKind.keys()]
      .filter((k) => !RESOURCE_SITE_KIND_ORDER.includes(k as (typeof RESOURCE_SITE_KIND_ORDER)[number]))
      .sort((a, b) => a.localeCompare(b)),
  ];

  const title = `Resources (${resources.length})`;

  return (
    <section className="mb-1">
      <div className="flex min-w-0 items-center gap-1 bg-cyan-900/30 px-1.5 py-0.5 text-xs font-bold uppercase tracking-widest">
        {!open ? (
          <span
            className={`shrink-0 font-semibold ${allActive ? "text-green-400" : "text-red-400"}`}
            title={allActive ? "All resource sites active" : "At least one resource site inactive"}
            aria-hidden
          >
            ●
          </span>
        ) : null}
        <span className="min-w-0 flex-1 truncate text-cyber-cyan">{title}</span>
        <ResourcesCreditsRollupLabel items={resources} className="text-xs text-cyber-cyan/80" />
        <span
          className={RESOURCE_ROLLUP_MONO}
          title="Estimated value of material held at production sites (mine storage)"
        >
          stor {cr(mineStorageValueCr)}
        </span>
        {nextAt ? (
          <span className="shrink-0 font-mono text-xs font-normal normal-case tracking-normal text-cyber-cyan">
            <Countdown targetIso={nextAt} prefix="next:" onExpired={onReload} />
          </span>
        ) : null}
        <PanelExpandButton
          open={open}
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="shrink-0"
        />
      </div>
      {open ? (
        <div className="border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-xs">
          {orderedKindKeys.map((kindKey) => (
            <ResourcesCategoryGroup
              key={kindKey}
              kindKey={kindKey}
              items={byKind.get(kindKey) ?? []}
              resourceNames={resourceNames}
              onRepairRig={onRepairRig}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}

const PROPERTY_KIND_ORDER = ["commercial", "industrial", "residential"] as const;

function propertyKindBucket(zone: string | undefined): (typeof PROPERTY_KIND_ORDER)[number] {
  const z = (zone || "residential").toLowerCase();
  if (z === "commercial" || z === "industrial" || z === "residential") return z;
  return "residential";
}

function propertyKindTitle(kind: (typeof PROPERTY_KIND_ORDER)[number]): string {
  if (kind === "commercial") return "Commercial";
  if (kind === "industrial") return "Industrial";
  return "Residential";
}

function PropertyRealtyAgentMark({ agent }: { agent: DashboardProperty["realtyAgent"] }) {
  if (agent === "nano") {
    return (
      <span
        className="inline-flex h-4 shrink-0 items-center justify-center rounded border border-cyan-600/55 bg-cyan-950/90 px-[3px] text-ui-caption font-bold leading-none text-cyber-cyan"
        title="NanoMegaPlex Real Estate"
        aria-label="Purchased from NanoMegaPlex Real Estate"
      >
        N
      </span>
    );
  }
  if (agent === "frontier") {
    return (
      <span
        className="inline-flex h-4 shrink-0 items-center justify-center rounded border border-amber-600/55 bg-amber-950/85 px-[3px] text-ui-caption font-bold leading-none text-amber-200"
        title="Frontier Real Estate"
        aria-label="Purchased from Frontier Real Estate"
      >
        F
      </span>
    );
  }
  return null;
}

function PropertiesKindGroup({
  kind,
  items,
}: {
  kind: (typeof PROPERTY_KIND_ORDER)[number];
  items: DashboardProperty[];
}) {
  const title = `${propertyKindTitle(kind)} (${items.length})`;
  const [open, setOpen] = useDashboardPanelOpen(`properties:${kind}`, true);

  let rollupCr = 0;
  let rollupCrRows = 0;
  for (const p of items) {
    const v = p.referenceListPriceCr;
    if (v != null && !Number.isNaN(v)) {
      rollupCr += v;
      rollupCrRows += 1;
    }
  }

  return (
    <div className="mb-1 last:mb-0">
      <div className="flex min-w-0 items-center gap-1 bg-cyan-900/20 px-1 py-0.5 text-ui-caption font-bold uppercase tracking-widest">
        <span className="min-w-0 flex-1 truncate text-cyber-cyan">{title}</span>
        <PropertiesCreditsRollupLabel sumCr={rollupCr} counted={rollupCrRows} rowCount={items.length} />
        <PanelExpandButton
          open={open}
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="shrink-0"
        />
      </div>
      {open ? (
        <div className={`${DASHBOARD_SCROLL_LIST_CLASS} space-y-0 pt-0.5`}>
          {items.map((p) => (
            <Row key={p.claimId}>
              <div className="flex min-w-0 flex-1 items-center gap-1">
                <PropertyRealtyAgentMark agent={p.realtyAgent} />
                <span className="min-w-0 flex-1 truncate text-foreground">{p.claimKey}</span>
              </div>
              <span className="text-xs text-ui-muted">
                {p.zone} T{p.tier}
              </span>
              {p.hasBuiltOnParcel ? (
                <span
                  className="inline-flex shrink-0 items-center justify-center text-lg leading-none text-cyber-cyan"
                  title="Something built on this property"
                  aria-label="Something built on this property"
                >
                  ★
                </span>
              ) : null}
              {p.structureUpgradesAvailable ? (
                <span
                  className="inline-flex shrink-0 items-center justify-center text-xs leading-none text-amber-400"
                  title="Further structure upgrade available"
                  aria-label="Further structure upgrade available"
                >
                  ▲
                </span>
              ) : null}
              {p.referenceListPriceCr != null ? (
                <span className="font-mono text-ui-muted">{cr(p.referenceListPriceCr)}</span>
              ) : null}
              <TinyLink href={`/properties/${p.claimId}`}>→</TinyLink>
            </Row>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function personalStorageRow(raw: PersonalStorageEntry | number): {
  tons: number;
  estimatedValueCr: number | null;
} {
  if (typeof raw === "number") return { tons: raw, estimatedValueCr: null };
  return { tons: raw.tons, estimatedValueCr: raw.estimatedValueCr };
}

function aggregatePersonalStorageRollups(buckets: PersonalStorageBuckets): {
  totalTons: number;
  sumCr: number;
  crRows: number;
  rowCount: number;
} {
  let totalTons = 0;
  let sumCr = 0;
  let crRows = 0;
  let rowCount = 0;
  for (const bucket of [buckets.mine, buckets.flora, buckets.fauna]) {
    for (const raw of Object.values(bucket)) {
      rowCount += 1;
      const { tons, estimatedValueCr } = personalStorageRow(raw);
      totalTons += Number(tons) || 0;
      if (estimatedValueCr != null && !Number.isNaN(estimatedValueCr)) {
        sumCr += estimatedValueCr;
        crRows += 1;
      }
    }
  }
  return { totalTons, sumCr, crRows, rowCount };
}

const PERSONAL_STORAGE_TABLE_GRID =
  "grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(5.5rem,auto)_minmax(5.5rem,auto)] gap-x-2 items-baseline";

function PersonalStorageKindGroup({
  panelSlug,
  title,
  weights,
  resourceNames,
}: {
  panelSlug: string;
  title: string;
  weights: Record<string, PersonalStorageEntry | number>;
  resourceNames: ReturnType<typeof useResourceNameLookup>;
}) {
  const entries = Object.entries(weights).sort(([a], [b]) => a.localeCompare(b));
  const [open, setOpen] = useDashboardPanelOpen(`personal-storage:${panelSlug}`, true);
  if (entries.length === 0) return null;

  let rollupTons = 0;
  let rollupCr = 0;
  let rollupCrRows = 0;
  for (const [, raw] of entries) {
    const { tons, estimatedValueCr } = personalStorageRow(raw);
    rollupTons += Number(tons) || 0;
    if (estimatedValueCr != null && !Number.isNaN(estimatedValueCr)) {
      rollupCr += estimatedValueCr;
      rollupCrRows += 1;
    }
  }
  const headerTitle = `${title} (${entries.length})`;

  return (
    <div className="mb-1 last:mb-0">
      <div className="flex min-w-0 items-center gap-1 bg-cyan-900/20 px-1 py-0.5 text-ui-caption font-bold uppercase tracking-widest">
        <span className="min-w-0 flex-1 truncate text-cyber-cyan">{headerTitle}</span>
        <PersonalStorageTonsRollupLabel tons={rollupTons} />
        <PersonalStorageCreditsRollupLabel sumCr={rollupCr} counted={rollupCrRows} rowCount={entries.length} />
        <PanelExpandButton
          open={open}
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${headerTitle}`}
          className="shrink-0"
        />
      </div>
      {open ? (
        <>
          <div
            className={`mb-0.5 ${PERSONAL_STORAGE_TABLE_GRID} pt-0.5 font-mono text-ui-caption uppercase tracking-wide text-ui-muted`}
          >
            <span className="min-w-0 truncate">resource</span>
            <span className="text-right tabular-nums">t</span>
            <span className="text-right tabular-nums" title="Estimated value at local bids (credits)">
              est.cr
            </span>
          </div>
          <div className={`${DASHBOARD_SCROLL_LIST_CLASS} space-y-0`}>
            {entries.map(([key, raw]) => {
              const { tons, estimatedValueCr } = personalStorageRow(raw);
              return (
                <div key={key} className={PERSONAL_STORAGE_TABLE_GRID}>
                  <span className="min-w-0 truncate text-foreground">
                    {displayResourceName(key, resourceNames)}
                  </span>
                  <span className="text-right font-mono tabular-nums text-foreground">
                    {Number(tons).toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    <span className="text-ui-muted">t</span>
                  </span>
                  <span
                    className="text-right font-mono tabular-nums text-ui-muted"
                    title="Estimated value at local bids (credits)"
                  >
                    {cr(estimatedValueCr)}
                  </span>
                </div>
              );
            })}
          </div>
        </>
      ) : null}
    </div>
  );
}

function PersonalStoragePanel({ buckets }: { buckets: PersonalStorageBuckets }) {
  const resourceNames = useResourceNameLookup();
  const n =
    Object.keys(buckets.mine).length +
    Object.keys(buckets.flora).length +
    Object.keys(buckets.fauna).length;
  if (n === 0) return null;

  const psRollup = aggregatePersonalStorageRollups(buckets);

  return (
    <Panel
      panelKey="personal-storage"
      title={`Personal storage (${n})`}
      headerActions={
        <>
          <PersonalStorageTonsRollupLabel tons={psRollup.totalTons} />
          <PersonalStorageCreditsRollupLabel
            sumCr={psRollup.sumCr}
            counted={psRollup.crRows}
            rowCount={psRollup.rowCount}
          />
        </>
      }
    >
      <PersonalStorageKindGroup
        panelSlug="mine"
        title="Mined"
        weights={buckets.mine}
        resourceNames={resourceNames}
      />
      <PersonalStorageKindGroup
        panelSlug="flora"
        title="Flora"
        weights={buckets.flora}
        resourceNames={resourceNames}
      />
      <PersonalStorageKindGroup
        panelSlug="fauna"
        title="Fauna"
        weights={buckets.fauna}
        resourceNames={resourceNames}
      />
    </Panel>
  );
}

function PropertiesPanel({ properties }: { properties: DashboardProperty[] }) {
  if (properties.length === 0) return null;

  const byKind: Record<(typeof PROPERTY_KIND_ORDER)[number], DashboardProperty[]> = {
    commercial: [],
    industrial: [],
    residential: [],
  };
  for (const p of properties) {
    byKind[propertyKindBucket(p.zone)].push(p);
  }
  for (const k of PROPERTY_KIND_ORDER) {
    byKind[k].sort((a, b) => a.claimKey.localeCompare(b.claimKey));
  }

  let propsRollupCr = 0;
  let propsRollupCrRows = 0;
  for (const p of properties) {
    const v = p.referenceListPriceCr;
    if (v != null && !Number.isNaN(v)) {
      propsRollupCr += v;
      propsRollupCrRows += 1;
    }
  }

  return (
    <Panel
      panelKey="properties"
      title={`Properties (${properties.length})`}
      headerActions={
        <PropertiesCreditsRollupLabel
          sumCr={propsRollupCr}
          counted={propsRollupCrRows}
          rowCount={properties.length}
        />
      }
    >
      {PROPERTY_KIND_ORDER.map((kind) => {
        const items = byKind[kind];
        if (items.length === 0) return null;
        return <PropertiesKindGroup key={kind} kind={kind} items={items} />;
      })}
    </Panel>
  );
}

function ClaimsNavPanel({ claims }: { claims: ControlSurfaceState["nav"]["claims"] }) {
  if (claims.length === 0) return null;
  return (
    <Panel panelKey="claims" title={`Claims (${claims.length})`}>
      <div className={DASHBOARD_SCROLL_LIST_CLASS}>
        {claims.map((c) => (
          <div key={c.href} className="flex flex-wrap items-center gap-1">
            <TinyLink href={c.href}>{c.label}</TinyLink>
            {c.volumeTier ? <Badge label={c.volumeTier} cls={c.volumeTierCls} /> : null}
            {c.resourceRarityTier ? <Badge label={c.resourceRarityTier} cls={c.resourceRarityTierCls} /> : null}
            <span
              className="inline-block rounded bg-zinc-700/60 px-1 text-ui-caption font-bold uppercase tabular-nums text-ui-muted"
              title="Est. value per production cycle (local bids)"
            >
              {c.estimatedValuePerCycle != null ? `${c.estimatedValuePerCycle.toLocaleString()}cr/c` : "—"}
            </span>
          </div>
        ))}
      </div>
    </Panel>
  );
}

export function ControlSurfaceMainPanels({ data, onReload }: { data: ControlSurfaceState; onReload: () => void }) {
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const { messages: gameLog } = useMsgStream();

  const run = useCallback(
    async (fn: () => Promise<unknown>) => {
      if (busy) return;
      setBusy(true);
      setFlash(null);
      try {
        await fn();
        onReload();
      } catch (e) {
        setFlash(e instanceof Error ? e.message : "Action failed");
      } finally {
        setBusy(false);
      }
    },
    [busy, onReload],
  );

  const ackAlert = useCallback((alertId: string) => run(() => dashboardAckAlert({ alertId })), [run]);
  const ackAllAlerts = useCallback(() => run(() => dashboardAckAllAlerts()), [run]);
  const deployMineCb = useCallback(
    (packageId: number, claimId: number) => run(() => mineDeploy({ packageId, claimId })),
    [run],
  );
  const repairRigCb = useCallback((siteId: number) => run(() => mineRepairRig({ siteId })), [run]);
  const claimChallengeCb = useCallback(
    (challengeId: string, windowKey: string) =>
      run(() => claimChallengeReward({ challengeId, windowKey })),
    [run],
  );
  const claimCadenceCb = useCallback(
    (cadence: string) => run(() => claimChallengeRewardsForCadence({ cadence })),
    [run],
  );

  const claimAllChallengesCb = useCallback(
    (cadences: string[]) => run(() => claimChallengeRewardsAll({ cadences })),
    [run],
  );

  return (
    <div className="dark min-h-svh bg-zinc-950 font-mono text-xs text-foreground">
      {flash ? (
        <div className="sticky top-0 z-50 bg-red-900/80 px-2 py-1 text-red-200">
          {flash}{" "}
          <button type="button" onClick={() => setFlash(null)} className="ml-2 text-red-300">
            ×
          </button>
        </div>
      ) : null}
      {data.character?.room ? (
        <LocationBanner
          ambient={data.ambient ?? EMPTY_ROOM_AMBIENT}
          roomName={data.character.room}
          variant="compact"
          messages={gameLog}
        />
      ) : null}
      <div className="grid min-h-0 grid-cols-1 md:min-h-svh md:grid-cols-2">
        <div className="min-h-0 min-w-0 overflow-y-auto border-r border-cyan-900/40 p-1.5 md:min-h-0">
          <DashboardMissionsPanel
            missions={data.missions ?? EMPTY_MISSIONS}
            quests={data.quests ?? null}
            roomExits={data.roomExits}
            onChanged={onReload}
            gameLog={gameLog}
          />
          <MineDeploymentPanel inventory={data.inventory} onDeploy={deployMineCb} busy={busy} />
        </div>
        <div className="min-h-0 min-w-0 overflow-y-auto p-1.5 md:min-h-0">
          {data.challenges ? (
            <ChallengesPanel
              challenges={data.challenges}
              onClaimChallenge={claimChallengeCb}
              onClaimCadence={claimCadenceCb}
              onClaimAll={claimAllChallengesCb}
              claimBusy={busy}
            />
          ) : null}
          {data.groupedAlerts ? (
            <AlertsPanel grouped={data.groupedAlerts} onAck={ackAlert} onAckAll={ackAllAlerts} busy={busy} />
          ) : null}
          <ShipsPanel ships={data.ships} />
          {busy ? <div className="mb-1 text-xs text-ui-muted">Working...</div> : null}
          <InventoryPanel inventory={data.inventory} />
          <ResourcesPanel
            resources={data.resources ?? data.mines}
            market={data.market}
            miningNextCycleAt={data.miningNextCycleAt ?? ""}
            mineStorageValueCr={data.productionTotalStoredValue ?? data.miningTotalStoredValue ?? 0}
            onReload={onReload}
            onRepairRig={repairRigCb}
          />
          <PersonalStoragePanel
            buckets={data.personalStorage ?? { mine: {}, flora: {}, fauna: {} }}
          />
          <PropertiesPanel properties={data.properties} />
          <ClaimsNavPanel claims={data.nav.claims} />
        </div>
      </div>
    </div>
  );
}
