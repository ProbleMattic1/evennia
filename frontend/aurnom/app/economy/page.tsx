"use client";

import Link from "next/link";

import { EconomyMiningAccrualCard } from "@/components/economy-mining-accrual-card";
import { EconomyMinerPayoutHero } from "@/components/economy-miner-payout-hero";
import { useControlSurface } from "@/components/control-surface-provider";

export default function EconomyPage() {
  const { data, error, loading } = useControlSurface();

  if (loading && !data) {
    return (
      <main className="min-h-svh bg-zinc-950 p-4 font-mono text-[11px] text-cyan-300">
        Loading economy…
      </main>
    );
  }

  if (error && !data) {
    return (
      <main className="min-h-svh bg-zinc-950 p-4 font-mono text-[11px] text-red-400">
        {error}
      </main>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <main className="dark relative min-h-svh overflow-x-hidden bg-zinc-950 p-3 font-mono text-[11px] text-zinc-300 md:p-6">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_120%_80%_at_50%_-20%,rgba(34,211,238,0.14),transparent_55%),radial-gradient(ellipse_80%_50%_at_100%_50%,rgba(6,182,212,0.06),transparent_50%)] opacity-90"
        aria-hidden
      />
      <div className="relative z-10 mx-auto max-w-6xl">
        <header className="mb-3 flex flex-wrap items-baseline gap-3 border-b border-cyan-900/40 pb-3">
          <h1 className="text-sm font-bold uppercase tracking-widest text-cyan-400">Economy</h1>
          <Link
            href="/"
            className="ml-auto rounded border border-cyan-800/60 px-2 py-1 text-cyan-400 hover:bg-cyan-950/50"
          >
            ← Control surface
          </Link>
        </header>

        <section
          className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
          aria-label="Economy metrics"
        >
          <EconomyMinerPayoutHero
            lastCycleCr={data.minerPayoutLastCycleCr}
            totalCr={data.minerPayoutTotalCr}
            miningNextCycleAt={data.miningNextCycleAt}
            miningDeliveryPeriodSeconds={data.miningDeliveryPeriodSeconds}
          />
          <EconomyMiningAccrualCard data={data} />
        </section>
      </div>
    </main>
  );
}
