"use client";

import { useReducedMotion } from "motion/react";

import type { ControlSurfaceState } from "@/lib/control-surface-api";
import {
  estimatedPipelineTotalCr,
  floraPortfolioAccruedCr,
  miningCycleProgress,
  miningPeriodSeconds,
  miningPortfolioAccruedCr,
  plantOrePoolsDisplay,
  portfolioStoredOreTonsBreakdown,
} from "@/lib/economy-dashboard-derive";
import { EconomyStatCard } from "@/components/economy-stat-card";
import { useOdometerInt } from "@/lib/use-odometer-value";
import { useServerAnchoredTimeMs } from "@/lib/use-server-anchored-time";

const ACCRUAL_HINT =
  "Linear estimate within the current UTC delivery slot from server rates and bids. " +
  "Not wallet credits; real ticks can differ (hazards, wear, storage, bid moves).";

const ORE_TONS_HINT =
  "Site tons = sum of storageUsed on your owned production sites (mining vs flora). " +
  "Plant lines are separate pools from the server: receiving bay, refinery input, queues.";

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
  const ore = portfolioStoredOreTonsBreakdown(data);
  const plant = plantOrePoolsDisplay(data);

  return (
    <>
      <p className="text-[9px] text-ui-soft">
        Stored (bid): sites{" "}
        {(data.productionTotalStoredValue ?? data.miningTotalStoredValue)?.toLocaleString() ?? 0} cr · plant silo{" "}
        {data.miningPersonalStoredValue?.toLocaleString() ?? 0} cr
      </p>
      <p className="mt-2 text-[9px] text-ui-soft">
        Est. this slot (accrual): mining {miningAccrued.toLocaleString()} cr
        {floraAccrued > 0 ? <> · flora {floraAccrued.toLocaleString()} cr</> : null}
      </p>
      <p className="mt-1 font-mono text-[11px] tabular-nums text-cyan-200/90">
        Pipeline (stored + accrual est.): {pipelineOdo.toLocaleString()} cr
      </p>
      <div className="mt-3 border-t border-cyan-950/60 pt-2" title={ORE_TONS_HINT}>
        <p className="text-[8px] uppercase tracking-wider text-ui-muted">Ore mass (sites)</p>
        <p className="mt-0.5 font-mono text-[11px] tabular-nums text-zinc-200">
          {ore.totalTons.toFixed(1)} t total
          <span className="font-normal text-ui-soft">
            {" "}
            · mining {ore.miningSiteTons.toFixed(1)} · flora {ore.floraSiteTons.toFixed(1)}
          </span>
        </p>
        {plant ? (
          <>
            <p className="mt-2 text-[8px] uppercase tracking-wider text-ui-muted">
              Plant — raw path ({plant.plantName})
            </p>
            <p className="mt-0.5 text-[9px] text-ui-soft">
              Receiving bay {plant.rawBayTons.toFixed(1)} t
              {plant.myOreQueuedTons != null ? (
                <> · My queue {plant.myOreQueuedTons.toFixed(1)} t</>
              ) : (
                <> · My queue —</>
              )}
              <> · Miner queue {plant.minerQueueOreTons.toFixed(1)} t</>
            </p>
            <p className="mt-2 text-[8px] uppercase tracking-wider text-ui-muted">Plant — refinery</p>
            <p className="mt-0.5 text-[9px] text-ui-soft">Input inventory {plant.refineryInputTons.toFixed(1)} t</p>
          </>
        ) : null}
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
