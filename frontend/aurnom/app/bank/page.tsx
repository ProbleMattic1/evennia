"use client";

import { useCallback } from "react";
import Link from "next/link";

import { ExitGrid } from "@/components/exit-grid";
import { StoryPanel } from "@/components/story-panel";
import { getBankState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

export default function BankPage() {
  const loader = useCallback(() => getBankState(), []);
  const { data, error, loading } = useUiResource(loader);

  if (loading) {
    return (
      <main className="main-content">
        <p className="text-sm text-zinc-500 dark:text-cyan-500/80">Loading bank state…</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="main-content">
        <p className="text-sm text-red-600 dark:text-red-400">Failed to load bank state: {error ?? "Unknown error"}</p>
      </main>
    );
  }

  return (
    <main className="main-content">
      <header className="page-header flex items-center justify-between border-b border-zinc-200 py-3 pl-2 dark:border-cyan-900/50">
        <div className="px-2">
          <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">{data.bankName}</h1>
          <p className="mt-0.5 text-[12px] text-zinc-500 dark:text-cyan-500/80">{data.roomName}</p>
        </div>
        <Link
          href="/play?room=Alpha%20Prime%20Central%20Reserve"
          className="rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-800 hover:bg-zinc-100 dark:border-cyan-700/50 dark:text-cyan-400 dark:hover:bg-cyan-950/40 dark:hover:text-cyan-300"
        >
          Back to Play
        </Link>
      </header>

      <div className="flex flex-col gap-2 px-2 py-2">
        <ExitGrid exits={data.exits} />
        <StoryPanel title="Bank Output" lines={data.storyLines} />
        <section className="border-b border-zinc-100 px-2 py-2 dark:border-cyan-900/30">
          <h2 className="section-label">Treasury</h2>
          <p className="mt-1 font-mono text-sm font-semibold tabular-nums text-zinc-800 dark:text-zinc-200">
            {data.treasuryBalance.toLocaleString()}{" "}
            <span className="text-amber-700 dark:text-amber-400">cr</span>
          </p>
          <p className="mt-0.5 font-mono text-[11px] text-zinc-500 dark:text-cyan-500/70">{data.treasuryAccount}</p>
        </section>

        <section className="border-b border-zinc-100 px-2 py-2 dark:border-cyan-900/30">
          <h2 className="section-label">Treasury activity</h2>
          <p className="mt-1 text-sm text-zinc-600 dark:text-cyan-500/80">
            Every ledger movement through Alpha Prime ({data.treasuryAccount}): taxes, license fees, repair tax,
            and disbursements. Positive Δ is a credit to the treasury; negative is a debit.
          </p>
          {data.treasuryTransactionLog.length > 0 ? (
            <div className="mt-2 overflow-x-auto rounded border border-zinc-200 dark:border-cyan-900/50">
              <table className="w-full min-w-[40rem] border-collapse text-left text-[12px]">
                <thead>
                  <tr className="border-b border-zinc-200 bg-zinc-50 dark:border-cyan-900/50 dark:bg-zinc-950/80">
                    <th className="px-2 py-1.5 font-medium text-zinc-600 dark:text-cyan-500/90">Time</th>
                    <th className="px-2 py-1.5 font-medium text-zinc-600 dark:text-cyan-500/90">Type</th>
                    <th className="px-2 py-1.5 font-medium text-zinc-600 dark:text-cyan-500/90">From</th>
                    <th className="px-2 py-1.5 font-medium text-zinc-600 dark:text-cyan-500/90">To</th>
                    <th className="px-2 py-1.5 font-medium text-zinc-600 dark:text-cyan-500/90">Memo</th>
                    <th className="px-2 py-1.5 text-right font-medium text-zinc-600 dark:text-cyan-500/90">
                      Δ treasury
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.treasuryTransactionLog.map((row, i) => {
                    const signed = row.signedAmount;
                    const signCls =
                      signed > 0
                        ? "text-emerald-700 dark:text-emerald-400"
                        : signed < 0
                          ? "text-red-700 dark:text-red-400"
                          : "text-zinc-600 dark:text-zinc-400";
                    let timeLabel = row.timestamp;
                    try {
                      const d = new Date(row.timestamp);
                      if (!Number.isNaN(d.getTime())) {
                        timeLabel = d.toLocaleString(undefined, {
                          dateStyle: "short",
                          timeStyle: "short",
                        });
                      }
                    } catch {
                      /* keep raw */
                    }
                    return (
                      <tr
                        key={`treasury-${row.timestamp}-${row.type}-${i}`}
                        className="border-b border-zinc-100 last:border-0 dark:border-cyan-950/60"
                      >
                        <td className="whitespace-nowrap px-2 py-1.5 font-mono text-zinc-600 dark:text-zinc-400">
                          {timeLabel}
                        </td>
                        <td className="px-2 py-1.5 font-mono text-zinc-700 dark:text-zinc-300">{row.type}</td>
                        <td className="max-w-[9rem] truncate px-2 py-1.5 font-mono text-zinc-600 dark:text-cyan-500/80" title={row.fromAccount ?? ""}>
                          {row.fromAccount ?? "—"}
                        </td>
                        <td className="max-w-[9rem] truncate px-2 py-1.5 font-mono text-zinc-600 dark:text-cyan-500/80" title={row.toAccount ?? ""}>
                          {row.toAccount ?? "—"}
                        </td>
                        <td className="max-w-[12rem] truncate px-2 py-1.5 text-zinc-600 dark:text-cyan-500/80" title={row.memo}>
                          {row.memo || "—"}
                        </td>
                        <td className={`px-2 py-1.5 text-right font-mono tabular-nums font-semibold ${signCls}`}>
                          {signed > 0 ? "+" : ""}
                          {signed.toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="mt-2 text-sm text-zinc-500 dark:text-cyan-500/80">No treasury movements recorded yet.</p>
          )}
        </section>

        <section className="border-b border-zinc-100 px-2 py-2 dark:border-cyan-900/30">
          <h2 className="section-label">Your account</h2>
          {data.credits != null ? (
            <p className="mt-1 font-mono text-sm tabular-nums text-zinc-700 dark:text-zinc-300">
              Balance{" "}
              <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                {data.credits.toLocaleString()}
              </span>{" "}
              <span className="text-amber-700 dark:text-amber-400">cr</span>
            </p>
          ) : (
            <p className="mt-1 text-sm text-zinc-500 dark:text-cyan-500/80">
              Sign in to view your personal balance and movements involving your account.
            </p>
          )}
          {data.transactionLog && data.transactionLog.length > 0 ? (
            <div className="mt-2 overflow-x-auto rounded border border-zinc-200 dark:border-cyan-900/50">
              <table className="w-full min-w-[32rem] border-collapse text-left text-[12px]">
                <thead>
                  <tr className="border-b border-zinc-200 bg-zinc-50 dark:border-cyan-900/50 dark:bg-zinc-950/80">
                    <th className="px-2 py-1.5 font-medium text-zinc-600 dark:text-cyan-500/90">Time</th>
                    <th className="px-2 py-1.5 font-medium text-zinc-600 dark:text-cyan-500/90">Type</th>
                    <th className="px-2 py-1.5 font-medium text-zinc-600 dark:text-cyan-500/90">Memo</th>
                    <th className="px-2 py-1.5 text-right font-medium text-zinc-600 dark:text-cyan-500/90">
                      Δ cr
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.transactionLog.map((row, i) => {
                    const signed = row.signedAmount;
                    const signCls =
                      signed > 0
                        ? "text-emerald-700 dark:text-emerald-400"
                        : signed < 0
                          ? "text-red-700 dark:text-red-400"
                          : "text-zinc-600 dark:text-zinc-400";
                    let timeLabel = row.timestamp;
                    try {
                      const d = new Date(row.timestamp);
                      if (!Number.isNaN(d.getTime())) {
                        timeLabel = d.toLocaleString(undefined, {
                          dateStyle: "short",
                          timeStyle: "short",
                        });
                      }
                    } catch {
                      /* keep raw */
                    }
                    return (
                      <tr
                        key={`you-${row.timestamp}-${row.type}-${i}`}
                        className="border-b border-zinc-100 last:border-0 dark:border-cyan-950/60"
                      >
                        <td className="whitespace-nowrap px-2 py-1.5 font-mono text-zinc-600 dark:text-zinc-400">
                          {timeLabel}
                        </td>
                        <td className="px-2 py-1.5 font-mono text-zinc-700 dark:text-zinc-300">
                          {row.type}
                        </td>
                        <td className="max-w-[14rem] truncate px-2 py-1.5 text-zinc-600 dark:text-cyan-500/80" title={row.memo}>
                          {row.memo || "—"}
                        </td>
                        <td className={`px-2 py-1.5 text-right font-mono tabular-nums font-semibold ${signCls}`}>
                          {signed > 0 ? "+" : ""}
                          {signed.toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : data.credits != null ? (
            <p className="mt-2 text-sm text-zinc-500 dark:text-cyan-500/80">No personal ledger movements yet.</p>
          ) : null}
        </section>
      </div>
    </main>
  );
}
