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
    return <p className="text-xs text-red-400">{err}</p>;
  }
  if (!data) {
    return <p className="text-xs text-ui-muted">Loading world economy…</p>;
  }

  const mining = (data.world.mining as Record<string, number> | undefined) ?? {};
  const ledger = (data.world.ledger as Record<string, number> | undefined) ?? {};
  const meter = data.meters[0];
  const live =
    meter && !reduceMotion ? linearAccruingValue(meter, now) : (meter?.valueAtEnd ?? 0);

  return (
    <section className="mb-4 rounded border border-cyan-900/40 bg-zinc-950/90 p-3">
      <p className="text-ui-caption uppercase tracking-widest text-ui-muted">World economy</p>
      <p className="mt-1 font-mono text-sm tabular-nums text-cyber-cyan">
        {Math.floor(live).toLocaleString()} <span className="text-ui-muted">cr</span>
        <span className="ml-2 text-xs text-ui-soft">slot meter (implied)</span>
      </p>
      <div className="mt-2 grid gap-1 text-xs text-ui-muted sm:grid-cols-2">
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
