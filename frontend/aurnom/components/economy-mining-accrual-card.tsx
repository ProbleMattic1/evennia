"use client";

import { useReducedMotion } from "motion/react";

import type { ControlSurfaceState } from "@/lib/control-surface-api";
import {
  estimatedPipelineTotalCr,
  faunaPortfolioAccruedCr,
  floraPortfolioAccruedCr,
  miningCycleProgress,
  miningPeriodSeconds,
  miningPortfolioAccruedCr,
} from "@/lib/economy-dashboard-derive";
import { EconomyStatCard } from "@/components/economy-stat-card";
import { useOdometerInt } from "@/lib/use-odometer-value";
import { useServerAnchoredTimeMs } from "@/lib/use-server-anchored-time";

const ACCRUAL_HINT =
  "Linear estimate within the current UTC delivery slot from server rates and bids. " +
  "Not wallet credits; real ticks can differ (hazards, wear, storage, bid moves).";

function formatBoundaryShort(iso: string | undefined) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString(undefined, {
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/** Shared metrics: use inside a card (economy page) or inside a larger dashboard panel. */
export function EconomyMiningAccrualBody({ data }: { data: ControlSurfaceState }) {
  const reduceMotion = useReducedMotion();
  const nowMs = useServerAnchoredTimeMs(data.serverTimeIso);
  const pipelineTarget = estimatedPipelineTotalCr(data, nowMs);
  const pipelineOdoRaw = useOdometerInt(pipelineTarget, 24);
  const pipelineOdo = reduceMotion ? pipelineTarget : pipelineOdoRaw;
  const miningAccrued = miningPortfolioAccruedCr(data, nowMs);
  const floraAccrued = floraPortfolioAccruedCr(data, nowMs);
  const faunaAccrued = faunaPortfolioAccruedCr(data, nowMs);

  return (
    <>
      <p className="text-[9px] text-ui-soft">
        Stored (bid): sites{" "}
        {(data.productionTotalStoredValue ?? data.miningTotalStoredValue)?.toLocaleString() ?? 0} cr · plant silo{" "}
        {data.miningPersonalStoredValue?.toLocaleString() ?? 0} cr
      </p>
      <div className="mt-2">
        <p className="text-[8px] uppercase tracking-wide text-ui-soft">Est. this slot (accrual)</p>
        <p
          className="mt-0.5 break-words font-mono text-[0.5625rem] font-semibold leading-tight tracking-tight text-cyan-400 sm:text-[0.625rem]"
          title="Linear accrual estimate by stream this slot"
        >
          mining {miningAccrued.toLocaleString()} cr
          {floraAccrued > 0 ? <> · flora {floraAccrued.toLocaleString()} cr</> : null}
          {faunaAccrued > 0 ? <> · fauna {faunaAccrued.toLocaleString()} cr</> : null}
        </p>
      </div>
      <div className="mt-3">
        <p className="text-[8px] uppercase tracking-wide text-ui-soft">Pipeline (stored + accrual est.)</p>
        <div
          className={`pipeline-matrix-frame mt-1 px-2 py-2 sm:px-2.5 sm:py-2.5 ${reduceMotion ? "" : "pipeline-matrix-frame--motion"}`}
        >
          <p
            className="pipeline-matrix-readout relative z-[2] break-all font-mono text-[2.25rem] font-semibold leading-[1.05] tracking-tight tabular-nums sm:text-[2.5rem]"
            title="Stored bid value plus accrual estimate"
          >
            {pipelineOdo.toLocaleString()} cr
          </p>
        </div>
      </div>
    </>
  );
}

/** Stat card for grids (e.g. `/economy` next to miner payouts). */
export function EconomyMiningAccrualCard({ data }: { data: ControlSurfaceState }) {
  const nowMs = useServerAnchoredTimeMs(data.serverTimeIso);
  const period = miningPeriodSeconds(data);
  const progress = miningCycleProgress(nowMs, data.miningNextCycleAt, period);
  const pct = Math.round(progress * 100);
  const nextShort = formatBoundaryShort(data.miningNextCycleAt);

  return (
    <EconomyStatCard
      title="Live production (est.)"
      hintTitle={ACCRUAL_HINT}
      headerRight={
        nextShort ? (
          <span className="text-[9px] tabular-nums text-ui-soft" title="Mining grid boundary">
            slot {pct}% · {nextShort}
          </span>
        ) : (
          <span className="text-[9px] tabular-nums text-ui-soft">slot {pct}%</span>
        )
      }
    >
      <EconomyMiningAccrualBody data={data} />
    </EconomyStatCard>
  );
}
