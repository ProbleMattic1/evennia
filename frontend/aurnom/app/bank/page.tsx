"use client";

import { Suspense, useCallback } from "react";
import { useSearchParams } from "next/navigation";

import { CsButtonLink, CsColumns, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { ExitGrid } from "@/components/exit-grid";
import { StoryPanel } from "@/components/story-panel";
import { getBankState } from "@/lib/ui-api";
import { useUiResource } from "@/lib/use-ui-resource";

function BankPageInner() {
  const searchParams = useSearchParams();
  const venue = searchParams.get("venue")?.trim() || undefined;
  const loader = useCallback(() => getBankState(venue), [venue]);
  const { data, error, loading } = useUiResource(loader);

  if (loading) {
    return (
      <CsPage>
        <p className="text-sm text-ui-accent-readable">Loading bank state…</p>
      </CsPage>
    );
  }

  if (error || !data) {
    return (
      <CsPage>
        <p className="text-sm text-red-600 dark:text-red-400">Failed to load bank state: {error ?? "Unknown error"}</p>
      </CsPage>
    );
  }

  return (
    <CsPage>
      <CsHeader
        title={data.bankName}
        subtitle={data.roomName}
        actions={<CsButtonLink href="/">Back to dashboard</CsButtonLink>}
      />
      <CsColumns
        left={
          <>
            <CsPanel title="Destinations">
              <ExitGrid exits={data.exits} />
            </CsPanel>
            <CsPanel title="Bank Output">
              <StoryPanel title="Bank Output" lines={data.storyLines} />
            </CsPanel>
            <CsPanel title="Treasury">
              <p className="mt-1 font-mono text-sm font-semibold tabular-nums text-foreground">
                {data.treasuryBalance.toLocaleString()}<span className="text-amber-400">cr</span>
              </p>
              <p className="mt-0.5 font-mono text-xs text-ui-muted">{data.treasuryAccount}</p>
            </CsPanel>
          </>
        }
        right={
          <>
            <CsPanel title="Treasury Activity">
              <p className="mt-1 text-sm text-ui-muted">
                Every ledger movement through {data.bankName} ({data.treasuryAccount}): taxes, license fees, repair tax,
                and disbursements. Positive Δ is a credit to the treasury; negative is a debit.
              </p>
              {data.treasuryTransactionLog.length > 0 ? (
                <div className="mt-2 overflow-x-auto rounded border border-cyan-900/50">
                  <table className="w-full min-w-[40rem] border-collapse text-left text-xs">
                    <thead>
                      <tr className="border-b border-cyan-900/50 bg-zinc-950/80">
                        <th className="px-2 py-1.5 font-medium text-cyber-cyan">Time</th>
                        <th className="px-2 py-1.5 font-medium text-cyber-cyan">Type</th>
                        <th className="px-2 py-1.5 font-medium text-cyber-cyan">From</th>
                        <th className="px-2 py-1.5 font-medium text-cyber-cyan">To</th>
                        <th className="px-2 py-1.5 font-medium text-cyber-cyan">Memo</th>
                        <th className="px-2 py-1.5 text-right font-medium text-cyber-cyan">Δ treasury</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.treasuryTransactionLog.map((row, i) => {
                        const signed = row.signedAmount;
                        const signCls =
                          signed > 0
                            ? "text-emerald-400"
                            : signed < 0
                              ? "text-red-400"
                              : "text-ui-muted";
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
                            className="border-b border-cyan-950/60 last:border-0"
                          >
                            <td className="whitespace-nowrap px-2 py-1.5 font-mono text-ui-muted">{timeLabel}</td>
                            <td className="px-2 py-1.5 font-mono text-foreground">{row.type}</td>
                            <td className="max-w-[9rem] truncate px-2 py-1.5 font-mono text-ui-accent-readable" title={row.fromAccount ?? ""}>
                              {row.fromAccount ?? "—"}
                            </td>
                            <td className="max-w-[9rem] truncate px-2 py-1.5 font-mono text-ui-accent-readable" title={row.toAccount ?? ""}>
                              {row.toAccount ?? "—"}
                            </td>
                            <td className="max-w-[12rem] truncate px-2 py-1.5 text-ui-accent-readable" title={row.memo}>
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
                <p className="mt-2 text-sm text-ui-muted">No treasury movements recorded yet.</p>
              )}
            </CsPanel>
            <CsPanel title="Your Account">
              {data.credits != null ? (
                <p className="mt-1 font-mono text-sm tabular-nums text-foreground">
                  Balance <span className="font-semibold text-foreground">{data.credits.toLocaleString()}</span>
                  <span className="text-amber-400">cr</span>
                </p>
              ) : (
                <p className="mt-1 text-sm text-ui-muted">
                  Sign in to view your personal balance and movements involving your account.
                </p>
              )}
              {data.transactionLog && data.transactionLog.length > 0 ? (
                <div className="mt-2 overflow-x-auto rounded border border-cyan-900/50">
                  <table className="w-full min-w-[32rem] border-collapse text-left text-xs">
                    <thead>
                      <tr className="border-b border-cyan-900/50 bg-zinc-950/80">
                        <th className="px-2 py-1.5 font-medium text-cyber-cyan">Time</th>
                        <th className="px-2 py-1.5 font-medium text-cyber-cyan">Type</th>
                        <th className="px-2 py-1.5 font-medium text-cyber-cyan">Memo</th>
                        <th className="px-2 py-1.5 text-right font-medium text-cyber-cyan">Δcr</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.transactionLog.map((row, i) => {
                        const signed = row.signedAmount;
                        const signCls =
                          signed > 0
                            ? "text-emerald-400"
                            : signed < 0
                              ? "text-red-400"
                              : "text-ui-muted";
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
                            className="border-b border-cyan-950/60 last:border-0"
                          >
                            <td className="whitespace-nowrap px-2 py-1.5 font-mono text-ui-muted">{timeLabel}</td>
                            <td className="px-2 py-1.5 font-mono text-foreground">{row.type}</td>
                            <td className="max-w-[14rem] truncate px-2 py-1.5 text-ui-accent-readable" title={row.memo}>
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
                <p className="mt-2 text-sm text-ui-muted">No personal ledger movements yet.</p>
              ) : null}
            </CsPanel>
          </>
        }
      />
    </CsPage>
  );
}

export default function BankPage() {
  return (
    <Suspense
      fallback={
        <CsPage>
          <p className="text-sm text-ui-accent-readable">Loading bank state…</p>
        </CsPage>
      }
    >
      <BankPageInner />
    </Suspense>
  );
}
