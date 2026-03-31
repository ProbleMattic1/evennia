"use client";

import { useReducedMotion } from "motion/react";

import type { ControlSurfaceState, WorldProductionPipelineSnapshot } from "@/lib/control-surface-api";
import {
  faunaPortfolioAccruedCr,
  floraPortfolioAccruedCr,
  miningCycleProgress,
  miningPeriodSeconds,
  miningPortfolioAccruedCr,
  portfolioImpliedAccrualCrPerHour,
} from "@/lib/economy-dashboard-derive";
import { EconomyStatCard } from "@/components/economy-stat-card";
import { formatCr } from "@/lib/format-units";
import { getRunningLedger, reconcileImpliedRunningLedger } from "@/lib/implied-accrual-running-totals";
import { useOdometerInt } from "@/lib/use-odometer-value";
import { useServerAnchoredTimeMs } from "@/lib/use-server-anchored-time";

const ACCRUAL_HINT =
  "Linear estimate within the current UTC delivery slot from server rates and bids. " +
  "Not wallet credits; real ticks can differ (hazards, wear, storage, bid moves).";

const WORLD_TELEMETRY_HINT =
  "World figures from economy_world_telemetry snapshot (~60s interval), not recomputed each poll.";

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
  const miningAccrued = miningPortfolioAccruedCr(data, nowMs);
  const floraAccrued = floraPortfolioAccruedCr(data, nowMs);
  const faunaAccrued = faunaPortfolioAccruedCr(data, nowMs);
  const userStoredSites = data.productionTotalStoredValue ?? data.miningTotalStoredValue ?? 0;
  const userImpliedCrPerHour = portfolioImpliedAccrualCrPerHour(data);
  const worldImpliedCrPerHour = data.worldProductionPipeline?.impliedAccrualCrPerHourTotal ?? 0;
  const { youTarget, worldTarget } = reconcileImpliedRunningLedger(
    getRunningLedger(),
    nowMs,
    userImpliedCrPerHour,
    worldImpliedCrPerHour,
  );
  const perFrameYou = Math.max(1, Math.ceil(userImpliedCrPerHour / 216000));
  const perFrameWorld = Math.max(1, Math.ceil(worldImpliedCrPerHour / 216000));
  const snapYou = perFrameYou * 120;
  const snapWorld = perFrameWorld * 120;
  const userImpliedOdoRaw = useOdometerInt(youTarget, perFrameYou, snapYou);
  const worldImpliedOdoRaw = useOdometerInt(worldTarget, perFrameWorld, snapWorld);
  const userImpliedDisplay = reduceMotion ? youTarget : userImpliedOdoRaw;
  const worldImpliedDisplay = reduceMotion ? worldTarget : worldImpliedOdoRaw;
  const wpp = data.worldProductionPipeline;
  const w: WorldProductionPipelineSnapshot =
    wpp ??
    ({
      storedSitesBidCr: 0,
      accrualThisSlotEstimatedCr: 0,
      impliedAccrualCrPerHourTotal: 0,
      estimatedPipelineTotalCr: 0,
      playerCharacterCount: 0,
    } satisfies WorldProductionPipelineSnapshot);

  const matrixFrameCls = `pipeline-matrix-frame px-2 py-2 sm:px-2.5 sm:py-2.5 ${reduceMotion ? "" : "pipeline-matrix-frame--motion"}`;
  const matrixReadoutCls =
    "pipeline-matrix-readout relative z-[2] break-all font-mono text-ui-pipeline-readout-secondary font-semibold tracking-tight tabular-nums";
  const rateReadoutCls =
    "pipeline-matrix-readout relative z-[2] whitespace-nowrap font-mono text-ui-pipeline-readout-secondary font-semibold tracking-tight tabular-nums";

  return (
    <>
      <p className="text-ui-caption text-ui-soft">
        Stored (bid): sites{" "}
        {(data.productionTotalStoredValue ?? data.miningTotalStoredValue)?.toLocaleString() ?? 0}cr · plant silo{" "}
        {data.miningPersonalStoredValue?.toLocaleString() ?? 0}cr
      </p>
      <div className="mt-2">
        <p className="text-ui-overline uppercase tracking-wide text-ui-soft">Est. this slot (accrual)</p>
        <p
          className="mt-0.5 break-words font-mono text-ui-caption font-semibold leading-tight tracking-tight text-cyber-cyan sm:text-xs"
          title="Linear accrual estimate by stream this slot"
        >
          mining {miningAccrued.toLocaleString()}cr
          {floraAccrued > 0 ? <> · flora {floraAccrued.toLocaleString()}cr</> : null}
          {faunaAccrued > 0 ? <> · fauna {faunaAccrued.toLocaleString()}cr</> : null}
        </p>
      </div>
      <div className="mt-3">
        <p className="text-ui-overline uppercase tracking-wide text-ui-soft">Stored (sites, bid)</p>
        <div
          className="mt-1 flex flex-wrap gap-2"
          title={"Sites only (bid-valued site storage); not plant silo. " + WORLD_TELEMETRY_HINT}
        >
          <div className={`${matrixFrameCls} min-w-[min(100%,8.5rem)] flex-1`}>
            <p className="relative z-[2] text-ui-overline uppercase tracking-wide text-ui-soft">You</p>
            <p className={matrixReadoutCls}>{userStoredSites.toLocaleString()}cr</p>
          </div>
          <div className={`${matrixFrameCls} min-w-[min(100%,8.5rem)] flex-1`}>
            <p className="relative z-[2] text-ui-overline uppercase tracking-wide text-ui-soft">World</p>
            <p className={matrixReadoutCls}>{(w.storedSitesBidCr ?? 0).toLocaleString()}cr</p>
          </div>
        </div>
      </div>
      <div className="mt-3">
        <p className="text-ui-overline uppercase tracking-wide text-ui-soft">Implied accrual running (est.)</p>
        <p className="mt-0.5 font-mono text-ui-caption tabular-nums text-ui-soft">
          UTC day + carry · at {userImpliedCrPerHour.toLocaleString()} /{" "}
          {worldImpliedCrPerHour.toLocaleString()}cr/h
        </p>
        <div
          className="mt-1 flex flex-wrap gap-2"
          title={
            "Grows continuously from server time at the implied cr/h rate for the current UTC calendar day. " +
            "At UTC midnight, the previous day closes at 24× the last seen rate and is added to carry (persisted in this browser) so the meter does not reset to zero. " +
            WORLD_TELEMETRY_HINT
          }
        >
          <div className={`${matrixFrameCls} min-w-[min(100%,8.5rem)] flex-1`}>
            <p className="relative z-[2] text-ui-overline uppercase tracking-wide text-ui-soft">You</p>
            <p className={rateReadoutCls}>{formatCr(userImpliedDisplay)}</p>
          </div>
          <div className={`${matrixFrameCls} min-w-[min(100%,8.5rem)] flex-1`}>
            <p className="relative z-[2] text-ui-overline uppercase tracking-wide text-ui-soft">World</p>
            <p className={rateReadoutCls}>{formatCr(worldImpliedDisplay)}</p>
          </div>
        </div>
      </div>
      <div className="mt-3">
        <p className="text-ui-overline uppercase tracking-wide text-ui-soft">
          All players (est., sum of portfolios)
        </p>
        <div
          className={`${matrixFrameCls} mt-1`}
          title={
            w.note ??
            "Sum of per-character pipeline estimates; updated on telemetry interval, not wallet credits."
          }
        >
          <p className={matrixReadoutCls}>{(w.estimatedPipelineTotalCr ?? 0).toLocaleString()}cr</p>
          <p className="relative z-[2] mt-1 font-mono text-ui-caption tabular-nums text-ui-soft">
            {w.playerCharacterCount ?? 0} chars
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
          <span className="text-ui-caption tabular-nums text-ui-soft" title="Mining grid boundary">
            slot {pct}% · {nextShort}
          </span>
        ) : (
          <span className="text-ui-caption tabular-nums text-ui-soft">slot {pct}%</span>
        )
      }
    >
      <EconomyMiningAccrualBody data={data} />
    </EconomyStatCard>
  );
}
