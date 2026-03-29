"use client";

import { useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";

import { linearAccruingValue } from "@/lib/economy-world-meters";
import { getEconomyWorldState, type EconomyWorldPayload } from "@/lib/ui-api";

export function EconomyWorldPanel() {
  const reduceMotion = useReducedMotion();
  const [data, setData] = useState<EconomyWorldPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    let c = false;
    (async () => {
      try {
        const p = await getEconomyWorldState();
        if (!c) setData(p);
      } catch (e) {
        if (!c) setErr(e instanceof Error ? e.message : "economy-world failed");
      }
    })();
    return () => {
      c = true;
    };
  }, []);

  useEffect(() => {
    if (reduceMotion) return;
    const id = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(id);
  }, [reduceMotion]);

  if (err) {
    return <p className="text-[10px] text-red-400">{err}</p>;
  }
  if (!data) {
    return <p className="text-[10px] text-zinc-500">Loading world economy…</p>;
  }

  const mining = (data.world.mining as Record<string, number> | undefined) ?? {};
  const ledger = (data.world.ledger as Record<string, number> | undefined) ?? {};
  const meter = data.meters[0];
  const live =
    meter && !reduceMotion ? linearAccruingValue(meter, now) : (meter?.valueAtEnd ?? 0);

  return (
    <section className="mb-4 rounded border border-cyan-900/40 bg-zinc-950/90 p-3">
      <p className="text-[9px] uppercase tracking-widest text-zinc-500">World economy</p>
      <p className="mt-1 font-mono text-sm tabular-nums text-cyan-300">
        {Math.floor(live).toLocaleString()} <span className="text-zinc-500">cr</span>
        <span className="ml-2 text-[10px] text-zinc-600">slot meter (implied)</span>
      </p>
      <div className="mt-2 grid gap-1 text-[10px] text-zinc-400 sm:grid-cols-2">
        <span>sites {mining.siteCount ?? 0}</span>
        <span>active {mining.activeSiteCount ?? 0}</span>
        <span>producing {mining.producingSiteCount ?? 0}</span>
        <span>stored (bid) {(mining.storedValueBidCr ?? 0).toLocaleString()} cr</span>
        <span>treasury {(ledger.treasuryBalanceCr ?? 0).toLocaleString()} cr</span>
        <span>player mass {(ledger.playerCreditsMassCr ?? 0).toLocaleString()} cr</span>
      </div>
    </section>
  );
}
