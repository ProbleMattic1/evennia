"use client";

import Link from "next/link";
import { useCallback, useMemo, useState, type ReactNode } from "react";

import { Countdown } from "@/components/countdown";
import { DashboardMissionsPanel } from "@/components/dashboard-missions-panel";
import type { ControlSurfaceState, CsInventory } from "@/lib/control-surface-api";
import type {
  DashboardAlert,
  DashboardGroupedAlerts,
  DashboardMine,
  DashboardProperty,
  DashboardShip,
  MarketCommodity,
} from "@/lib/ui-api";
import { compositionToLines, buildResourceNameLookup, displayResourceName } from "@/lib/resource-display";
import { useDashboardPanelOpen } from "@/lib/use-dashboard-panel-open";
import { dashboardAckAlert, dashboardAckAllAlerts, mineDeploy, mineRepairRig } from "@/lib/ui-api";

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
      <div className="flex min-w-0 items-center gap-1 bg-cyan-900/30 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-cyan-300">
        <span className="min-w-0 truncate">{title}</span>
        <div className="ml-auto flex shrink-0 items-center gap-1 normal-case tracking-normal">
          {headerActions}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
            className="px-1 text-cyan-400 hover:text-cyan-300"
          >
            {open ? "▴" : "▸"}
          </button>
        </div>
      </div>
      {open ? <div className="border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-[11px]">{children}</div> : null}
    </section>
  );
}

function Kv({ k, v, dim }: { k: string; v: ReactNode; dim?: boolean }) {
  return (
    <div className="flex min-w-0 gap-1">
      <span className="shrink-0 text-ui-muted">{k}</span>
      <span className={`min-w-0 truncate font-mono ${dim ? "text-ui-muted" : "text-zinc-200"}`}>{v}</span>
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
      className="shrink-0 rounded border border-cyan-800/60 px-1 py-0 text-[10px] text-cyan-400 hover:bg-cyan-900/40"
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
      className={`shrink-0 rounded border px-1 py-0 text-[10px] disabled:opacity-40 ${
        danger
          ? "border-red-800/60 text-red-400 hover:bg-red-900/40"
          : "border-cyan-800/60 text-cyan-400 hover:bg-cyan-900/40"
      }`}
    >
      {children}
    </button>
  );
}

function Badge({ label, cls }: { label: string; cls?: string }) {
  const base = "inline-block rounded px-1 text-[9px] font-bold uppercase";
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

function cr(n: number | null | undefined) {
  if (n == null) return "—";
  return `${n.toLocaleString()} cr`;
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
      <div className="max-h-[min(220px,40vh)] min-h-[48px] overflow-y-auto overflow-x-hidden pr-0.5 [scrollbar-gutter:stable]">
        {all.map((a: DashboardAlert) => (
          <Row key={a.id} className="mb-0.5 items-start">
            <span className={`shrink-0 text-[9px] font-bold uppercase ${sevColor(a.severity)}`}>
              {a.severity[0].toUpperCase()}
            </span>
            <span className="min-w-0 flex-1 text-zinc-300">{a.title}</span>
            <TinyButton onClick={() => onAck(a.id)}>×</TinyButton>
          </Row>
        ))}
      </div>
    </Panel>
  );
}

function MarketPanel({ commodities }: { commodities: MarketCommodity[] }) {
  if (commodities.length === 0) return null;
  return (
    <Panel panelKey="market" title="Market">
      <table className="w-full table-fixed text-[10px]">
        <thead>
          <tr className="text-ui-muted">
            <th className="w-1/2 text-left font-normal">resource</th>
            <th className="w-1/4 text-right font-normal">sell</th>
            <th className="w-1/4 text-right font-normal">buy</th>
          </tr>
        </thead>
        <tbody>
          {commodities.map((c) => (
            <tr key={c.key} className="border-t border-zinc-800/60">
              <td className="truncate text-zinc-300">{c.name}</td>
              <td className="text-right font-mono text-green-400">{c.sellPriceCrPerTon.toLocaleString()}</td>
              <td className="text-right font-mono text-red-400">{c.buyPriceCrPerTon.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
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
            <div className="text-[10px] uppercase text-ui-muted">{title}</div>
            {rows.map((item) => (
              <Row key={`${bucketId}-${item.stacked && item.ids?.length ? item.ids.join("-") : item.id}-${item.key}`}>
                <span className="flex-1 truncate text-zinc-300">
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
          <label className="mt-1 block text-[10px] uppercase tracking-wide text-ui-muted">Package</label>
          <select
            className="w-full rounded border border-cyan-900/50 bg-zinc-900 px-1 py-0.5 text-[11px] text-zinc-200"
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

          <label className="mt-1 block text-[10px] uppercase tracking-wide text-ui-muted">Claim</label>
          <select
            className="w-full rounded border border-cyan-900/50 bg-zinc-900 px-1 py-0.5 text-[11px] text-zinc-200"
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

function ShipsPanel({ ships }: { ships: DashboardShip[] }) {
  if (ships.length === 0) return null;
  return (
    <Panel panelKey="ships" title={`Ships (${ships.length})`}>
      {ships.map((s) => (
        <Row key={s.id}>
          <span className="flex-1 truncate font-semibold text-zinc-200">
            {s.count && s.count > 1 ? `${s.count}× ` : ""}
            {s.key}
          </span>
          {s.state ? <span className="text-[10px] text-ui-muted">{s.state}</span> : null}
          {s.location ? <span className="text-[10px] text-ui-muted">{s.location}</span> : null}
        </Row>
      ))}
    </Panel>
  );
}

const RESOURCE_SITE_KIND_ORDER = ["mining_site", "flora_site"] as const;

function resourceSiteKindKey(m: DashboardMine): string {
  if (m.kind && String(m.kind).length > 0) return String(m.kind);
  if (m.siteKind === "flora") return "flora_site";
  return "mining_site";
}

function resourceCategoryTitle(kindKey: string): string {
  if (kindKey === "mining_site") return "Mines";
  if (kindKey === "flora_site") return "Flora harvesters";
  return kindKey
    .split("_")
    .map((w) => (w ? w.charAt(0).toUpperCase() + w.slice(1).toLowerCase() : w))
    .join(" ");
}

function visitProductionSiteLabel(m: DashboardMine): string {
  if (m.kind === "flora_site" || m.siteKind === "flora") return "Visit stand →";
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
            <span className="min-w-0 flex-1 truncate font-mono text-zinc-200">{m.key}</span>
            {m.rigWear != null && m.rigWear >= 70 ? (
              <button
                type="button"
                onClick={() => onRepairRig(m.id)}
                className="shrink-0 font-mono text-[10px] text-amber-400 hover:text-amber-300"
              >
                Repair rig ⚠
              </button>
            ) : null}
            {m.location ? (
              <span className="inline-flex translate-y-px">
                <TinyLink href={`/play?room=${encodeURIComponent(m.location)}`}>{visitProductionSiteLabel(m)}</TinyLink>
              </span>
            ) : null}
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-label={`${open ? "Collapse" : "Expand"} ${m.key}`}
              className="shrink-0 px-1 text-cyan-400 hover:text-cyan-300"
            >
              {open ? "▴" : "▸"}
            </button>
          </div>
          {m.volumeTier ? (
            <div className="mt-0.5 flex min-w-0 items-center gap-1.5">
              <Row>
                <Badge label={m.volumeTier} cls={m.volumeTierCls} />
                <Badge label={m.resourceRarityTier ?? ""} cls={m.resourceRarityTierCls} />
              </Row>
              {m.estimatedValuePerCycle != null ? (
                <span className="shrink-0 font-mono text-[10px] text-ui-muted">
                  {cr(m.estimatedValuePerCycle)}<span className="text-ui-soft"> yld</span>
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
      {open ? (
        <div className={`ml-3 mt-1 items-start gap-x-2 ${hasProduces ? "grid grid-cols-2" : ""}`}>
          <div className="min-w-0 space-y-0">
            <Kv k="storage" v={`${m.storageUsed}/${m.storageCapacity} t`} />
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
                    <span key={line.key} className="font-mono text-zinc-200">
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
      <div className="flex min-w-0 items-center gap-1 bg-cyan-900/20 px-1 py-0.5 text-[9px] font-bold uppercase tracking-widest text-cyan-300">
        {!open ? (
          <span
            className={`shrink-0 font-semibold ${allActive ? "text-green-400" : "text-red-400"}`}
            title={allActive ? "All sites in this category active" : "At least one site inactive"}
            aria-hidden
          >
            ●
          </span>
        ) : null}
        <span className="min-w-0 flex-1 truncate">{title}</span>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="shrink-0 px-1 text-cyan-400 hover:text-cyan-300"
        >
          {open ? "▴" : "▸"}
        </button>
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
  onReload,
  onRepairRig,
}: {
  resources: DashboardMine[];
  market: MarketCommodity[];
  miningNextCycleAt: string;
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
      <div className="flex min-w-0 items-center gap-1 bg-cyan-900/30 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-cyan-300">
        {!open ? (
          <span
            className={`shrink-0 font-semibold ${allActive ? "text-green-400" : "text-red-400"}`}
            title={allActive ? "All resource sites active" : "At least one resource site inactive"}
            aria-hidden
          >
            ●
          </span>
        ) : null}
        <span className="min-w-0 flex-1 truncate">{title}</span>
        {nextAt ? (
          <span className="shrink-0 font-mono text-[10px] font-normal normal-case tracking-normal text-cyan-300">
            <Countdown targetIso={nextAt} prefix="next:" onExpired={onReload} />
          </span>
        ) : null}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="shrink-0 px-1 text-cyan-400 hover:text-cyan-300"
        >
          {open ? "▴" : "▸"}
        </button>
      </div>
      {open ? (
        <div className="border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-[11px]">
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

function PropertiesKindGroup({
  kind,
  items,
}: {
  kind: (typeof PROPERTY_KIND_ORDER)[number];
  items: DashboardProperty[];
}) {
  const title = `${propertyKindTitle(kind)} (${items.length})`;
  const [open, setOpen] = useDashboardPanelOpen(`properties:${kind}`, true);

  return (
    <div className="mb-1 last:mb-0">
      <div className="flex min-w-0 items-center gap-1 bg-cyan-900/20 px-1 py-0.5 text-[9px] font-bold uppercase tracking-widest text-cyan-300">
        <span className="min-w-0 flex-1 truncate">{title}</span>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="shrink-0 px-1 text-cyan-400 hover:text-cyan-300"
        >
          {open ? "▴" : "▸"}
        </button>
      </div>
      {open ? (
        <div className="space-y-0 pt-0.5">
          {items.map((p) => (
            <Row key={p.claimId}>
              <span className="flex-1 truncate text-zinc-300">{p.claimKey}</span>
              <span className="text-[10px] text-ui-muted">
                {p.zone} T{p.tier}
              </span>
              {p.hasBuiltOnParcel ? (
                <span
                  className="inline-flex shrink-0 items-center justify-center text-[18px] leading-none text-cyan-400"
                  title="Something built on this property"
                  aria-label="Something built on this property"
                >
                  ★
                </span>
              ) : null}
              {p.structureUpgradesAvailable ? (
                <span
                  className="inline-flex shrink-0 items-center justify-center text-[10px] leading-none text-amber-400"
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

  return (
    <Panel panelKey="properties" title={`Properties (${properties.length})`}>
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
      {claims.map((c) => (
        <div key={c.href} className="flex flex-wrap items-center gap-1">
          <TinyLink href={c.href}>{c.label}</TinyLink>
          {c.volumeTier ? <Badge label={c.volumeTier} cls={c.volumeTierCls} /> : null}
          {c.resourceRarityTier ? <Badge label={c.resourceRarityTier} cls={c.resourceRarityTierCls} /> : null}
          <span
            className="inline-block rounded bg-zinc-700/60 px-1 text-[9px] font-bold uppercase tabular-nums text-ui-muted"
            title="Est. value per production cycle (local bids)"
          >
            {c.estimatedValuePerCycle != null ? `${c.estimatedValuePerCycle.toLocaleString()} cr/c` : "—"}
          </span>
        </div>
      ))}
    </Panel>
  );
}

export function ControlSurfaceMainPanels({ data, onReload }: { data: ControlSurfaceState; onReload: () => void }) {
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

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

  return (
    <div className="dark min-h-svh bg-zinc-950 font-mono text-[11px] text-zinc-300">
      {flash ? (
        <div className="sticky top-0 z-50 bg-red-900/80 px-2 py-1 text-red-200">
          {flash}{" "}
          <button type="button" onClick={() => setFlash(null)} className="ml-2 text-red-300">
            ×
          </button>
        </div>
      ) : null}
      <div className="grid min-h-svh grid-cols-2">
        <div className="min-w-0 overflow-y-auto border-r border-cyan-900/40 p-1.5">
          {data.missions ? (
            <DashboardMissionsPanel missions={data.missions} roomExits={data.roomExits} onChanged={onReload} />
          ) : null}
          <MineDeploymentPanel inventory={data.inventory} onDeploy={deployMineCb} busy={busy} />
          <ResourcesPanel
            resources={data.resources ?? data.mines}
            market={data.market}
            miningNextCycleAt={data.miningNextCycleAt ?? ""}
            onReload={onReload}
            onRepairRig={repairRigCb}
          />
        </div>
        <div className="min-w-0 overflow-y-auto p-1.5">
          {data.groupedAlerts ? (
            <AlertsPanel grouped={data.groupedAlerts} onAck={ackAlert} onAckAll={ackAllAlerts} busy={busy} />
          ) : null}
          {busy ? <div className="mb-1 text-[10px] text-ui-muted">Working...</div> : null}
          <InventoryPanel inventory={data.inventory} />
          <ShipsPanel ships={data.ships} />
          <PropertiesPanel properties={data.properties} />
          <ClaimsNavPanel claims={data.nav.claims} />
        </div>
      </div>
    </div>
  );
}
