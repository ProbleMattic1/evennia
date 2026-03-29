"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  motion,
  useMotionValue,
  useMotionValueEvent,
  useReducedMotion,
  useSpring,
} from "motion/react";

import type { ControlSurfaceState } from "@/lib/control-surface-api";
import {
  aggregateEstimatedComposition,
  formatCrPerSec,
  impliedPortfolioCrPerSec,
  impliedPortfolioTonsPerSec,
  miningCycleProgress,
  miningPeriodSeconds,
} from "@/lib/economy-dashboard-derive";
import { getMarketState } from "@/lib/ui-api";
import { useMarketHistory, seriesForKey } from "@/lib/use-market-history";

function CycleRing({ progress }: { progress: number }) {
  const pct = Math.round(progress * 100);
  return (
    <div
      className="relative size-24 shrink-0 rounded-full border border-cyan-900/50"
      style={{
        background: `conic-gradient(rgb(34 211 238) ${pct}%, rgb(39 39 42) 0)`,
      }}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Mining delivery cycle progress"
    >
      <div className="absolute inset-2 flex items-center justify-center rounded-full bg-zinc-950 text-[10px] text-cyan-300">
        {pct}%
      </div>
    </div>
  );
}

function SpringCrDisplay({ crPerSec, reduceMotion }: { crPerSec: number; reduceMotion: boolean }) {
  const mv = useMotionValue(crPerSec);
  const spring = useSpring(mv, { stiffness: 120, damping: 24 });
  const [display, setDisplay] = useState(crPerSec);

  useEffect(() => {
    mv.set(crPerSec);
  }, [crPerSec, mv]);

  useMotionValueEvent(spring, "change", (v) => {
    setDisplay(v);
  });

  if (reduceMotion) {
    return <span className="text-cyan-400/90">{formatCrPerSec(crPerSec)}</span>;
  }
  return <motion.span className="text-cyan-400/90">{formatCrPerSec(display)}</motion.span>;
}

export function EconomyDashboard({
  data,
  onReload,
}: {
  data: ControlSurfaceState;
  onReload: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const [now, setNow] = useState(() => Date.now());
  const { history, push } = useMarketHistory();

  const period = miningPeriodSeconds(data);
  const crPs = impliedPortfolioCrPerSec(data);
  const tPs = impliedPortfolioTonsPerSec(data);
  const progress = miningCycleProgress(now, data.miningNextCycleAt, period);

  const resourceSites = data.resources ?? data.mines ?? [];
  const compRows = useMemo(() => aggregateEstimatedComposition(resourceSites), [resourceSites]);
  const compChartData = useMemo(
    () => compRows.slice(0, 12).map((r) => ({ name: r.key, tons: Math.round(r.tons * 10) / 10 })),
    [compRows],
  );

  const primaryCommodityKey = data.market?.[0]?.key ?? "";

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const m = await getMarketState();
        if (!cancelled) push(m.commodities);
      } catch {
        /* ignore */
      }
    };
    void tick();
    const id = window.setInterval(tick, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [push]);

  const sparkData = useMemo(() => {
    if (!primaryCommodityKey) return [];
    return seriesForKey(history, primaryCommodityKey).map((p, i) => ({
      i,
      sell: p.sell,
      t: new Date(p.t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    }));
  }, [history, primaryCommodityKey]);

  const marketAlerts = useMemo(() => {
    const g = data.groupedAlerts;
    if (!g) return [];
    const rows = [...(g.critical ?? []), ...(g.warning ?? []), ...(g.info ?? [])];
    return rows.filter((a) => a.category === "market").slice(0, 8);
  }, [data.groupedAlerts]);

  const proc = data.processing;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="rounded border border-cyan-800/60 px-2 py-1 text-cyan-400 hover:bg-cyan-950/50"
          onClick={() => onReload()}
        >
          Sync
        </button>
        <p className="text-[10px] text-zinc-500">
          Implied rates assume the current cycle repeats every {period}s at today&apos;s bids.
        </p>
        {data.serverTimeIso ? (
          <span className="text-[10px] text-zinc-600">Server {data.serverTimeIso}</span>
        ) : null}
      </div>

      <section className="grid gap-3 md:grid-cols-[1fr_auto] md:items-center">
        <div className="rounded border border-cyan-900/40 bg-zinc-950/90 p-3">
          <p className="text-[9px] uppercase tracking-widest text-zinc-500">Portfolio mining (implied)</p>
          <div className="mt-1 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-cyan-300">
            <SpringCrDisplay crPerSec={crPs} reduceMotion={!!reduceMotion} />
            <span>{tPs.toFixed(4)} t/s</span>
            {data.credits != null ? (
              <span className="text-zinc-400">Wallet {data.credits.toLocaleString()} cr</span>
            ) : null}
            {data.treasuryBalance != null ? (
              <span className="text-zinc-500">Treasury {data.treasuryBalance.toLocaleString()} cr</span>
            ) : null}
            {data.propertyReferenceListValueTotalCr != null && data.propertyReferenceListValueTotalCr > 0 ? (
              <span className="text-zinc-500">
                Property ref. {data.propertyReferenceListValueTotalCr.toLocaleString()} cr
              </span>
            ) : null}
          </div>
          <p className="mt-2 text-[9px] text-zinc-600">
            Stored (bid): sites{" "}
            {(data.productionTotalStoredValue ?? data.miningTotalStoredValue)?.toLocaleString() ?? 0} cr · plant silo{" "}
            {data.miningPersonalStoredValue?.toLocaleString() ?? 0} cr
          </p>
        </div>
        <div className="flex items-center gap-3">
          <CycleRing progress={progress} />
          <div className="text-[10px] text-zinc-500">
            Next grid boundary
            <br />
            <span className="font-mono text-zinc-300">{data.miningNextCycleAt ?? "—"}</span>
          </div>
        </div>
      </section>

      <section className="flex h-52 min-h-0 flex-col rounded border border-cyan-900/40 bg-zinc-950/90 p-2">
        <p className="mb-1 shrink-0 px-1 text-[9px] uppercase tracking-widest text-zinc-500">
          Sample price spark
          {primaryCommodityKey ? (
            <>
              {" "}
              (<span className="text-zinc-400">{primaryCommodityKey}</span>)
            </>
          ) : null}
        </p>
        {sparkData.length === 0 ? (
          <p className="shrink-0 p-4 text-[10px] text-zinc-600">Collecting market samples…</p>
        ) : (
          <div className="min-h-0 min-w-0 flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={sparkData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis dataKey="t" tick={{ fontSize: 9, fill: "#71717a" }} />
                <YAxis tick={{ fontSize: 9, fill: "#71717a" }} width={44} />
                <Tooltip
                  contentStyle={{
                    background: "#09090b",
                    border: "1px solid #164e63",
                    fontSize: 11,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="sell"
                  stroke="#22d3ee"
                  fill="rgba(34,211,238,0.15)"
                  strokeWidth={1.5}
                  isAnimationActive={!reduceMotion}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      {compChartData.length > 0 ? (
        <section className="flex h-56 min-h-0 flex-col rounded border border-cyan-900/40 bg-zinc-950/90 p-2">
          <p className="mb-1 shrink-0 px-1 text-[9px] uppercase tracking-widest text-zinc-500">
            Estimated output mix (active resource sites, t/cycle implied)
          </p>
          <div className="min-h-0 min-w-0 flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={compChartData} layout="vertical" margin={{ top: 4, right: 8, left: 4, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 9, fill: "#71717a" }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={120}
                  tick={{ fontSize: 8, fill: "#a1a1aa" }}
                  interval={0}
                />
                <Tooltip
                  contentStyle={{
                    background: "#09090b",
                    border: "1px solid #164e63",
                    fontSize: 11,
                  }}
                />
                <Bar dataKey="tons" fill="rgba(34,211,238,0.55)" radius={[0, 4, 4, 0]} isAnimationActive={!reduceMotion} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      ) : null}

      {proc ? (
        <section className="rounded border border-cyan-900/40 bg-zinc-950/90 p-3">
          <p className="text-[9px] uppercase tracking-widest text-zinc-500">Processing plant</p>
          <p className="mt-0.5 text-[10px] text-zinc-400">{proc.plantName}</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <p className="text-[9px] text-zinc-600">Raw receiving</p>
              <p className="font-mono text-[11px] text-zinc-200">
                {proc.rawStorageUsed.toFixed(1)} / {proc.rawStorageCapacity.toFixed(1)} t
              </p>
              <div className="mt-1 h-1.5 overflow-hidden rounded bg-zinc-800">
                <div
                  className="h-full bg-cyan-600/80"
                  style={{
                    width: `${proc.rawStorageCapacity > 0 ? Math.min(100, (proc.rawStorageUsed / proc.rawStorageCapacity) * 100) : 0}%`,
                  }}
                />
              </div>
            </div>
            <div>
              <p className="text-[9px] text-zinc-600">Refinery (shared / attributed)</p>
              <p className="font-mono text-[11px] text-zinc-200">
                Pool {proc.refineryInputTons.toFixed(1)} t → {proc.refineryOutputValue.toLocaleString()} cr · Queue{" "}
                {proc.minerQueueOreTons.toFixed(1)} t · Attr. out {proc.minerOutputValueTotal.toLocaleString()} cr
              </p>
            </div>
            <div>
              <p className="text-[9px] text-zinc-600">Your queue / refined</p>
              <p className="font-mono text-[11px] text-zinc-200">
                Ore queued {proc.myOreQueued != null ? `${proc.myOreQueued.toFixed(1)} t` : "—"} · refined value{" "}
                {proc.myRefinedOutputValue != null ? `${proc.myRefinedOutputValue.toLocaleString()} cr` : "—"}
              </p>
            </div>
          </div>
        </section>
      ) : null}

      <section className="rounded border border-cyan-900/40 bg-zinc-950/90 p-3">
        <p className="text-[9px] uppercase tracking-widest text-zinc-500">Resources</p>
        {resourceSites.length === 0 ? (
          <p className="mt-1 text-[10px] text-zinc-600">No sites on file for this character.</p>
        ) : (
          <ul className="mt-2 max-h-48 space-y-1 overflow-auto">
            {resourceSites.map((m) => (
              <li
                key={m.id}
                className="flex flex-wrap items-baseline justify-between gap-2 border-b border-zinc-800/80 py-1 text-[10px]"
              >
                <span className="text-zinc-200">{m.key}</span>
                <span className="text-zinc-500">
                  {m.active ? "active" : "idle"} · est. {(m.estimatedValuePerCycle ?? 0).toLocaleString()} cr/cycle ·
                  storage {(m.storageUsed ?? 0).toFixed(0)}/{(m.storageCapacity ?? 0).toFixed(0)} t
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {marketAlerts.length > 0 ? (
        <section className="rounded border border-cyan-900/40 bg-zinc-950/90 p-3" aria-label="Market alerts">
          <p className="text-[9px] uppercase tracking-widest text-zinc-500">Market alerts</p>
          <ul className="mt-2 space-y-1">
            {marketAlerts.map((a) => (
              <li key={a.id} className="text-[10px] text-zinc-400">
                <span className="text-cyan-600/80">{a.severity}</span> · {a.title}
                {a.detail ? <span className="text-zinc-600"> — {a.detail}</span> : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
