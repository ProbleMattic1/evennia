"use client";

import Link from "next/link";
import { useCallback, useState, type ReactNode } from "react";

import { Countdown } from "@/components/countdown";
import type { ControlSurfaceState, CsInventory, CsProcessing } from "@/lib/control-surface-api";
import type {
  DashboardAlert,
  DashboardGroupedAlerts,
  DashboardMine,
  DashboardProperty,
  DashboardShip,
  MarketCommodity,
  MissionActive,
  MissionOpportunity,
  MissionsState,
} from "@/lib/ui-api";
import { acceptMission, chooseMission, dashboardAckAlert, mineDeploy } from "@/lib/ui-api";

function Panel({ title, children, className = "" }: { title: string; children: ReactNode; className?: string }) {
  const [open, setOpen] = useState(true);

  return (
    <section className={`mb-1 ${className}`}>
      <div className="flex items-center bg-cyan-900/30 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-cyan-500">
        <span>{title}</span>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
          className="ml-auto px-1 text-cyan-400 hover:text-cyan-300"
        >
          {open ? "▴" : "▸"}
        </button>
      </div>
      {open ? <div className="border border-cyan-900/40 bg-zinc-950/80 p-1.5 text-[11px]">{children}</div> : null}
    </section>
  );
}

function Kv({ k, v, dim }: { k: string; v: ReactNode; dim?: boolean }) {
  return (
    <div className="flex min-w-0 gap-1">
      <span className="shrink-0 text-zinc-500">{k}</span>
      <span className={`min-w-0 truncate font-mono ${dim ? "text-zinc-600" : "text-zinc-200"}`}>{v}</span>
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
    return <span className={`${base} bg-zinc-700/60 text-zinc-400`}>{label}</span>;
  }
  return <span className={`${base} bg-zinc-700/60 text-zinc-400`}>{label}</span>;
}

function cr(n: number | null | undefined) {
  if (n == null) return "—";
  return `${n.toLocaleString()} cr`;
}

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

function AlertsPanel({
  grouped,
  onAck,
}: {
  grouped: DashboardGroupedAlerts;
  onAck: (id: string) => void;
}) {
  const all = [...grouped.critical, ...grouped.warning, ...grouped.info];
  if (all.length === 0) return null;

  const sevColor = (s: string) => {
    if (s === "critical") return "text-red-400";
    if (s === "warning") return "text-yellow-400";
    return "text-zinc-400";
  };

  return (
    <Panel title={`Alerts (${all.length})`}>
      {all.map((a: DashboardAlert) => (
        <Row key={a.id} className="mb-0.5 items-start">
          <span className={`shrink-0 text-[9px] font-bold uppercase ${sevColor(a.severity)}`}>
            {a.severity[0].toUpperCase()}
          </span>
          <span className="min-w-0 flex-1 text-zinc-300">{a.title}</span>
          <TinyButton onClick={() => onAck(a.id)}>×</TinyButton>
        </Row>
      ))}
    </Panel>
  );
}

function MissionsPanel({
  missions,
  onAccept,
  onChoose,
}: {
  missions: MissionsState;
  onAccept: (id: string) => void;
  onChoose: (missionId: string, choiceId: string) => void;
}) {
  const { opportunities, active } = missions;

  return (
    <Panel title={`Missions (${active.length} active / ${opportunities.length} avail)`}>
      {active.map((m: MissionActive) => (
        <div key={m.id} className="mb-1 border-b border-zinc-800 pb-1 last:border-0 last:pb-0">
          <Row>
            <span className="font-semibold text-zinc-200">{m.title}</span>
            <span className="ml-auto text-[9px] text-zinc-500">{m.status}</span>
          </Row>
          {m.currentObjective ? (
            <div className="mt-0.5 text-zinc-400">{m.currentObjective.text ?? m.currentObjective.prompt}</div>
          ) : null}
          {m.currentObjective?.choices && m.currentObjective.choices.length > 0 ? (
            <div className="mt-0.5 flex flex-wrap gap-1">
              {m.currentObjective.choices.map((c) => (
                <TinyButton key={c.id} onClick={() => onChoose(m.id, c.id)}>
                  {c.label}
                </TinyButton>
              ))}
            </div>
          ) : null}
        </div>
      ))}

      {opportunities.length > 0 ? (
        <>
          <div className="mt-1 text-[10px] uppercase text-zinc-600">Available</div>
          {opportunities.map((op: MissionOpportunity) => (
            <Row key={op.id} className="mb-0.5">
              <span className="flex-1 text-zinc-400">{op.title}</span>
              <TinyButton onClick={() => onAccept(op.id)}>Accept</TinyButton>
            </Row>
          ))}
        </>
      ) : null}

      {active.length === 0 && opportunities.length === 0 ? (
        <span className="text-zinc-600">No missions available.</span>
      ) : null}
    </Panel>
  );
}

function MarketPanel({ commodities }: { commodities: MarketCommodity[] }) {
  if (commodities.length === 0) return null;
  return (
    <Panel title="Market">
      <table className="w-full table-fixed text-[10px]">
        <thead>
          <tr className="text-zinc-600">
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
  const total = inventory.claims.length + inventory.packages.length + inventory.other.length;
  if (total === 0) return null;

  return (
    <Panel title={`Inventory (${total})`}>
      {inventory.claims.length > 0 ? (
        <>
          <div className="text-[10px] uppercase text-zinc-600">Claims</div>
          {inventory.claims.map((item) => (
            <Row key={item.id}>
              <span className="flex-1 truncate text-zinc-300">{item.key}</span>
              {item.claimSpecs ? (
                <>
                  <Badge label={item.claimSpecs.volumeTier ?? ""} cls={item.claimSpecs.volumeTierCls} />
                  <Badge label={item.claimSpecs.resourceRarityTier ?? ""} cls={item.claimSpecs.resourceRarityTierCls} />
                </>
              ) : null}
              <TinyLink href={`/claims/${item.id}`}>→</TinyLink>
            </Row>
          ))}
        </>
      ) : null}
      {inventory.packages.length > 0 ? (
        <>
          <div className="mt-0.5 text-[10px] uppercase text-zinc-600">Packages</div>
          {inventory.packages.map((item) => (
            <Row key={item.id}>
              <span className="flex-1 truncate text-zinc-300">{item.key}</span>
              {item.estimatedValue != null ? <span className="font-mono text-zinc-500">{cr(item.estimatedValue)}</span> : null}
            </Row>
          ))}
        </>
      ) : null}
      {inventory.other.length > 0 ? (
        <>
          <div className="mt-0.5 text-[10px] uppercase text-zinc-600">Other</div>
          {inventory.other.map((item) => (
            <Row key={item.id}>
              <span className="flex-1 truncate text-zinc-300">
                {item.count && item.count > 1 ? `${item.count}× ` : ""}
                {item.key}
              </span>
            </Row>
          ))}
        </>
      ) : null}
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
  const packageRows = inventory.packages.flatMap((item) => {
    const ids = item.stacked && item.ids?.length ? item.ids : [item.id];
    return ids.map((id) => ({ ...item, id }));
  });
  const claimRows = inventory.claims.flatMap((item) => {
    const ids = item.stacked && item.ids?.length ? item.ids : [item.id];
    return ids.map((id) => ({ ...item, id }));
  });

  const [packageId, setPackageId] = useState<number | "">("");
  const [claimId, setClaimId] = useState<number | "">("");

  const canDeploy = typeof packageId === "number" && typeof claimId === "number";

  return (
    <Panel title="Mine Operations">
      <div className="space-y-1">
        <Kv k="packages" v={packageRows.length} />
        <Kv k="claims" v={claimRows.length} />
      </div>
      {packageRows.length === 0 || claimRows.length === 0 ? (
        <div className="mt-1 text-zinc-500">Need at least one mining package and one mining claim to deploy.</div>
      ) : (
        <>
          <label className="mt-1 block text-[10px] uppercase tracking-wide text-zinc-600">Package</label>
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

          <label className="mt-1 block text-[10px] uppercase tracking-wide text-zinc-600">Claim</label>
          <select
            className="w-full rounded border border-cyan-900/50 bg-zinc-900 px-1 py-0.5 text-[11px] text-zinc-200"
            value={claimId}
            onChange={(e) => setClaimId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Select claim</option>
            {claimRows.map((c) => (
              <option key={`claim-${c.id}`} value={c.id}>
                {c.key} #{c.id}
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
      )}
    </Panel>
  );
}

function ShipsPanel({ ships }: { ships: DashboardShip[] }) {
  if (ships.length === 0) return null;
  return (
    <Panel title={`Ships (${ships.length})`}>
      {ships.map((s) => (
        <Row key={s.id}>
          <span className="flex-1 truncate font-semibold text-zinc-200">
            {s.count && s.count > 1 ? `${s.count}× ` : ""}
            {s.key}
          </span>
          {s.state ? <span className="text-[10px] text-zinc-500">{s.state}</span> : null}
          {s.location ? <span className="text-[10px] text-zinc-600">{s.location}</span> : null}
        </Row>
      ))}
    </Panel>
  );
}

function MinesPanel({ mines, onReload }: { mines: DashboardMine[]; onReload: () => void }) {
  if (mines.length === 0) return null;
  return (
    <Panel title={`Mines (${mines.length})`}>
      {mines.map((m) => (
        <div key={m.key} className="mb-1 border-b border-zinc-800/60 pb-1 last:border-0 last:pb-0">
          <Row>
            <span className={`font-semibold ${m.active ? "text-green-400" : "text-zinc-500"}`}>{m.active ? "●" : "○"}</span>
            <span className="flex-1 truncate text-zinc-200">{m.key}</span>
          </Row>
          <div className="ml-3 space-y-0">
            {m.volumeTier ? (
              <Row>
                <Badge label={m.volumeTier} cls={m.volumeTierCls} />
                <Badge label={m.resourceRarityTier ?? ""} cls={m.resourceRarityTierCls} />
              </Row>
            ) : null}
            <Kv k="yield/cycle" v={cr(m.estimatedValuePerCycle)} />
            <Kv k="storage" v={`${m.storageUsed}/${m.storageCapacity} t`} />
            {m.rigWear != null ? <Kv k="rig wear" v={`${m.rigWear}%${!m.rigOperational ? " ⚠ offline" : ""}`} /> : null}
            {Object.keys(m.composition || {}).length > 0 ? (
              <Kv
                k="produces"
                v={Object.entries(m.composition)
                  .map(([k, v]) => `${k} ${Math.round(v * 100)}%`)
                  .join(", ")}
              />
            ) : null}
            {Object.keys(m.inventory || {}).length > 0 ? (
              <Kv
                k="stored"
                v={Object.entries(m.inventory)
                  .map(([k, v]) => `${k}: ${v.toFixed(1)}t`)
                  .join(" · ")}
              />
            ) : null}
            {m.nextCycleAt ? (
              <div className="text-zinc-500">
                <Countdown targetIso={m.nextCycleAt} prefix="next:" onExpired={onReload} />
              </div>
            ) : null}
            {m.location ? (
              <div className="mt-0.5">
                <TinyLink href={`/play?room=${encodeURIComponent(m.location)}`}>Visit mine →</TinyLink>
              </div>
            ) : null}
          </div>
        </div>
      ))}
    </Panel>
  );
}

function PropertiesPanel({ properties }: { properties: DashboardProperty[] }) {
  if (properties.length === 0) return null;
  return (
    <Panel title={`Properties (${properties.length})`}>
      {properties.map((p) => (
        <Row key={p.claimId}>
          <span className="flex-1 truncate text-zinc-300">{p.claimKey}</span>
          <span className="text-[10px] text-zinc-500">
            {p.zone} T{p.tier}
          </span>
          {p.referenceListPriceCr != null ? <span className="font-mono text-zinc-500">{cr(p.referenceListPriceCr)}</span> : null}
          <TinyLink href={`/properties/${p.claimId}`}>→</TinyLink>
        </Row>
      ))}
    </Panel>
  );
}

function ProcessingPanel({ processing }: { processing: CsProcessing }) {
  return (
    <Panel title="Processing">
      <Kv k="ore bay" v={`${processing.rawStorageUsed.toFixed(1)} / ${processing.rawStorageCapacity.toFixed(0)} t`} />
      <Kv k="refinery in" v={`${processing.refineryInputTons.toFixed(1)} t`} />
      <Kv k="refinery out" v={cr(processing.refineryOutputValue)} />
      {processing.myOreQueued != null ? <Kv k="my ore queued" v={`${processing.myOreQueued.toFixed(1)} t`} /> : null}
      {processing.myRefinedOutputValue != null ? <Kv k="my output" v={cr(processing.myRefinedOutputValue)} /> : null}
      {processing.myHaulers && processing.myHaulers.length > 0 ? (
        <div className="mt-0.5 text-[10px] text-zinc-500">
          {processing.myHaulers.length} hauler{processing.myHaulers.length !== 1 ? "s" : ""}
        </div>
      ) : null}
      <div className="mt-0.5 flex gap-2 text-[10px] text-zinc-600">
        <span>fee {pct(processing.processingFeeRate)}</span>
        <span>raw fee {pct(processing.rawSaleFeeRate)}</span>
      </div>
      <div className="mt-1">
        <TinyLink href="/processing">Open Plant →</TinyLink>
      </div>
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
  const acceptMissionCb = useCallback((opportunityId: string) => run(() => acceptMission({ opportunityId })), [run]);
  const chooseMissionCb = useCallback(
    (missionId: string, choiceId: string) => run(() => chooseMission({ missionId, choiceId })),
    [run],
  );
  const deployMineCb = useCallback(
    (packageId: number, claimId: number) => run(() => mineDeploy({ packageId, claimId })),
    [run],
  );

  return (
    <div className="min-h-svh bg-zinc-950 font-mono text-[11px] text-zinc-300">
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
          {data.missions ? <MissionsPanel missions={data.missions} onAccept={acceptMissionCb} onChoose={chooseMissionCb} /> : null}
          <MineDeploymentPanel inventory={data.inventory} onDeploy={deployMineCb} busy={busy} />
          <MinesPanel mines={data.mines} onReload={onReload} />
        </div>
        <div className="min-w-0 overflow-y-auto p-1.5">
          {data.groupedAlerts ? <AlertsPanel grouped={data.groupedAlerts} onAck={ackAlert} /> : null}
          {busy ? <div className="mb-1 text-[10px] text-zinc-500">Working...</div> : null}
          <InventoryPanel inventory={data.inventory} />
          <ShipsPanel ships={data.ships} />
          <PropertiesPanel properties={data.properties} />
          {data.processing ? <ProcessingPanel processing={data.processing} /> : null}
        </div>
      </div>
    </div>
  );
}
