"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { CsButtonLink, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { CommodityTickerStrip } from "@/components/commodity-ticker";
import { StoryPanel } from "@/components/story-panel";
import { formatCr as cr } from "@/lib/format-units";
import { displayResourceName } from "@/lib/resource-display";
import {
  getRefineryState,
  postRefineryCollectRefined,
  postRefineryFeedSilo,
  type RefineryCollectPreview,
  type RefineryState,
} from "@/lib/ui-api";
import { intervalMs, isUiPollPaused } from "@/lib/ui-refresh-policy";
import { useResourceNameLookup } from "@/lib/use-resource-name-lookup";
import { useUiResource } from "@/lib/use-ui-resource";

import type { PersonalStorageBuckets } from "@/lib/control-surface-api";

const EMPTY_PERSONAL_STORAGE: PersonalStorageBuckets = { mine: {}, flora: {}, fauna: {} };

const BTN =
  "rounded border border-cyan-700/50 bg-cyan-950/40 px-2 py-1 text-xs text-cyber-cyan hover:bg-cyan-900/50 disabled:opacity-50";

type StorageRow = { kind: string; key: string; tons: number; estimatedValueCr: number };

function flattenPersonalStorage(buckets: PersonalStorageBuckets | undefined | null): StorageRow[] {
  const b = buckets ?? EMPTY_PERSONAL_STORAGE;
  const order = ["mine", "flora", "fauna"] as const;
  const rows: StorageRow[] = [];
  for (const kind of order) {
    const w = b[kind] ?? {};
    for (const key of Object.keys(w).sort()) {
      const e = w[key];
      if (!e || typeof e.tons !== "number" || e.tons <= 0) continue;
      rows.push({
        kind,
        key,
        tons: e.tons,
        estimatedValueCr: e.estimatedValueCr ?? 0,
      });
    }
  }
  return rows;
}

function totalPersonalStorageTons(buckets: PersonalStorageBuckets | undefined | null): number {
  return flattenPersonalStorage(buckets).reduce((s, r) => s + r.tons, 0);
}

function StatRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-2 border-b border-zinc-100 py-1.5 last:border-0 dark:border-cyan-900/30">
      <span className="text-xs text-ui-muted">{label}</span>
      <span className="font-mono text-sm font-semibold tabular-nums text-zinc-800 dark:text-foreground">{value}</span>
    </div>
  );
}

function CollectPreviewBlock({ preview }: { preview: RefineryCollectPreview }) {
  return (
    <div className="mt-1 space-y-0">
      <StatRow label="Gross (base)" value={cr(preview.gross)} />
      <StatRow label="Processing fee" value={cr(preview.fee)} />
      <StatRow label="Net to you" value={cr(preview.net)} />
      <StatRow label="From treasury" value={cr(preview.required_from_treasury)} />
    </div>
  );
}

function RefineryPageInner() {
  const searchParams = useSearchParams();
  const venue = searchParams.get("venue")?.trim() || undefined;
  const loader = useCallback(() => getRefineryState(venue), [venue]);
  const { data, error, loading, reload } = useUiResource(loader);

  useEffect(() => {
    const ms = intervalMs("controlSurface", null);
    const id = window.setInterval(() => {
      if (!isUiPollPaused()) reload();
    }, ms);
    return () => window.clearInterval(id);
  }, [reload]);

  if (loading) {
    return (
      <CsPage>
        <p className="text-sm text-ui-accent-readable">Loading refinery…</p>
      </CsPage>
    );
  }

  if (error || !data) {
    return (
      <CsPage>
        <p className="text-sm text-red-600 dark:text-red-400">
          Failed to load refinery: {error ?? "Unknown error"}
        </p>
      </CsPage>
    );
  }

  return <RefineryLoaded data={data} reload={reload} />;
}

function RefineryLoaded({ data, reload }: { data: RefineryState; reload: () => void }) {
  const intervalSec = data.constants?.refineryEngineIntervalSeconds ?? 0;
  const feeRate = data.constants?.processingFeeRate ?? 0;
  const nameLookup = useResourceNameLookup();
  const [busy, setBusy] = useState(false);
  const [actionNote, setActionNote] = useState<string | null>(null);

  const venueId = data.venueId;
  const personalStorage = data.personalStorage ?? EMPTY_PERSONAL_STORAGE;
  const storageRows = useMemo(() => flattenPersonalStorage(personalStorage), [personalStorage]);
  const storageTons = useMemo(() => totalPersonalStorageTons(personalStorage), [personalStorage]);
  const canAct = Boolean(data.refineryWebActionsAllowed) && Boolean(venueId);

  const runAction = useCallback(
    async (fn: () => Promise<void>) => {
      setActionNote(null);
      setBusy(true);
      try {
        await fn();
        await reload();
      } catch (e) {
        setActionNote(e instanceof Error ? e.message : "Request failed");
      } finally {
        setBusy(false);
      }
    },
    [reload],
  );

  return (
    <CsPage>
      <CsHeader
        title={data.refineryKey}
        subtitle={data.roomName}
        actions={
          <div className="flex flex-wrap gap-1">
            <CsButtonLink href="/processing">Processing plant</CsButtonLink>
            <CsButtonLink href="/">Dashboard</CsButtonLink>
          </div>
        }
      />
      <div className="flex flex-col gap-1.5 p-1.5">
        <div className="min-w-0">
          <CsPanel title="Market strip">
            <CommodityTickerStrip />
          </CsPanel>
        </div>

        <div className="min-w-0">
          <CsPanel title="Overview">
            <StoryPanel title="Refinery" lines={data.storyLines} />
            <div className="mt-2 space-y-1 text-xs text-ui-accent-readable">
              {data.refineryCountInRoom > 1 ? (
                <p>
                  This room has <span className="font-mono">{data.refineryCountInRoom}</span> refineries; UI shows the
                  main plant refinery only.
                </p>
              ) : null}
              <p>
                Engine interval: <span className="font-mono tabular-nums">{intervalSec}s</span> · Collect fee rate:{" "}
                <span className="font-mono tabular-nums">{(feeRate * 100).toFixed(1)}%</span>
              </p>
            </div>

            <div className="mt-3 border-t border-cyan-900/30 pt-2">
              <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                <p className="text-[10px] uppercase tracking-wide text-cyber-cyan/90">Personal storage</p>
                <div className="flex flex-wrap items-center gap-1">
                  <span className="font-mono text-[10px] text-ui-muted tabular-nums">
                    Σ <span className="text-ui-accent-readable">{storageTons.toFixed(2)}</span> t
                  </span>
                  <button
                    type="button"
                    disabled={busy || !canAct || storageTons <= 0}
                    className={BTN}
                    onClick={() =>
                      void runAction(async () => {
                        await postRefineryFeedSilo({ venue: venueId, all: true });
                      })
                    }
                  >
                    Queue all (plant silo)
                  </button>
                </div>
              </div>
              <p className="mb-2 text-[10px] text-ui-muted">
                Totals merge your plant silo and local raw reserve. Web queue uses the assigned plant silo only (same as{" "}
                <span className="font-mono">feedrefinery silo</span> in-game).
              </p>
              {!data.myMinerOreQueueLines ? (
                <p className="text-xs text-ui-muted">Sign in with an active character to see storage and actions.</p>
              ) : !canAct ? (
                <p className="text-xs text-ui-muted">
                  Open Refinery from your station nav (your home venue) to queue or collect from the web.
                </p>
              ) : null}
              {actionNote ? <p className="mb-2 text-xs text-red-500 dark:text-red-400">{actionNote}</p> : null}
              {data.myMinerOreQueueLines ? (
                <div className="overflow-x-auto rounded border border-cyan-900/30">
                  <table className="w-full min-w-[360px] border-collapse text-left text-xs">
                    <thead className="bg-cyan-950/50 text-[10px] uppercase tracking-wide text-cyber-cyan/90">
                      <tr>
                        <th className="px-1.5 py-1 font-semibold">Kind</th>
                        <th className="px-1.5 py-1 font-semibold">Material</th>
                        <th className="px-1.5 py-1 font-semibold text-right">t</th>
                        <th className="px-1.5 py-1 font-semibold text-right">Est.</th>
                        <th className="px-1.5 py-1 font-semibold text-right"> </th>
                      </tr>
                    </thead>
                    <tbody>
                      {storageRows.length ? (
                        storageRows.map((r) => (
                          <tr key={`${r.kind}:${r.key}`} className="border-t border-cyan-900/20">
                            <td className="px-1.5 py-1 text-ui-muted">{r.kind}</td>
                            <td className="px-1.5 py-1 text-ui-accent-readable">
                              <span className="font-mono text-[10px] text-ui-muted">{r.key}</span>
                              <br />
                              {displayResourceName(r.key, nameLookup)}
                            </td>
                            <td className="px-1.5 py-1 text-right font-mono tabular-nums">{r.tons.toFixed(2)}</td>
                            <td className="px-1.5 py-1 text-right font-mono tabular-nums">{cr(r.estimatedValueCr)}</td>
                            <td className="px-1.5 py-1 text-right">
                              <button
                                type="button"
                                disabled={busy || !canAct}
                                className={BTN}
                                onClick={() =>
                                  void runAction(async () => {
                                    await postRefineryFeedSilo({
                                      venue: venueId,
                                      resourceKey: r.key,
                                      tons: r.tons,
                                    });
                                  })
                                }
                              >
                                Queue
                              </button>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={5} className="px-1.5 py-2 text-ui-muted">
                            No material in personal storage
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </div>
          </CsPanel>
        </div>

        <div className="grid gap-1.5 lg:grid-cols-2">
          <div className="min-w-0">
            <CsPanel title="Your queue">
              {!data.myMinerOreQueueLines ? (
                <p className="text-xs text-ui-muted">Sign in with an active character to see your refinery queue.</p>
              ) : (
                <div className="overflow-x-auto rounded border border-cyan-900/30">
                  <table className="w-full min-w-[280px] border-collapse text-left text-xs">
                    <thead className="bg-cyan-950/50 text-[10px] uppercase tracking-wide text-cyber-cyan/90">
                      <tr>
                        <th className="px-1.5 py-1 font-semibold">Material</th>
                        <th className="px-1.5 py-1 font-semibold text-right">t</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.myMinerOreQueueLines.length ? (
                        data.myMinerOreQueueLines.map((r) => (
                          <tr key={r.key} className="border-t border-cyan-900/20">
                            <td className="px-1.5 py-1 text-ui-accent-readable">
                              <span className="font-mono text-[10px] text-ui-muted">{r.key}</span>
                              <br />
                              {r.displayName}
                            </td>
                            <td className="px-1.5 py-1 text-right font-mono tabular-nums">{r.tons.toFixed(2)}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={2} className="px-1.5 py-2 text-ui-muted">
                            Nothing queued for you
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </CsPanel>
          </div>
          <div className="min-w-0">
            <CsPanel title="Your refined output & collect preview">
              {!data.myMinerOutputLines ? (
                <p className="text-xs text-ui-muted">Sign in with an active character to see your refined output.</p>
              ) : (
                <>
                  <div className="overflow-x-auto rounded border border-cyan-900/30">
                    <table className="w-full min-w-[320px] border-collapse text-left text-xs">
                      <thead className="bg-cyan-950/50 text-[10px] uppercase tracking-wide text-cyber-cyan/90">
                        <tr>
                          <th className="px-1.5 py-1 font-semibold">Product</th>
                          <th className="px-1.5 py-1 font-semibold text-right">Units</th>
                          <th className="px-1.5 py-1 font-semibold text-right">CR</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.myMinerOutputLines.length ? (
                          data.myMinerOutputLines.map((r) => (
                            <tr key={r.key} className="border-t border-cyan-900/20">
                              <td className="px-1.5 py-1 text-ui-accent-readable">
                                <span className="font-mono text-[10px] text-ui-muted">{r.key}</span>
                                <br />
                                {r.displayName}
                              </td>
                              <td className="px-1.5 py-1 text-right font-mono tabular-nums">{r.units.toFixed(2)}</td>
                              <td className="px-1.5 py-1 text-right font-mono tabular-nums">{cr(r.lineValueCr)}</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={3} className="px-1.5 py-2 text-ui-muted">
                              No refined units ready for you
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                  <div className="mt-2">
                    <p className="mb-1 text-xs text-ui-muted">Preview if you collected everything now (base values).</p>
                    {data.collectPreview ? <CollectPreviewBlock preview={data.collectPreview} /> : null}
                    {data.myMinerOutputLines && data.collectPreview && data.collectPreview.gross > 0 && canAct ? (
                      <button
                        type="button"
                        disabled={busy}
                        className={`mt-2 ${BTN}`}
                        onClick={() =>
                          void runAction(async () => {
                            await postRefineryCollectRefined({ venue: venueId });
                          })
                        }
                      >
                        Collect refined (treasury payout)
                      </button>
                    ) : null}
                    {data.myMinerOutputLines && !canAct && data.collectPreview && data.collectPreview.gross > 0 ? (
                      <p className="mt-1 text-[10px] text-ui-muted">
                        Use your home venue refinery link to collect from the web.
                      </p>
                    ) : null}
                  </div>
                </>
              )}
            </CsPanel>
          </div>
        </div>

        <div className="min-w-0">
          <CsPanel title={`Refining catalog (${data.recipes?.length ?? 0} recipes)`}>
            <div className="max-h-[420px] overflow-auto rounded border border-cyan-900/30">
              <table className="w-full min-w-[560px] border-collapse text-left text-[11px]">
                <thead className="sticky top-0 z-[1] bg-cyan-950/90 text-[10px] uppercase tracking-wide text-cyber-cyan/90">
                  <tr>
                    <th className="px-1.5 py-1 font-semibold">Key</th>
                    <th className="px-1.5 py-1 font-semibold">Name</th>
                    <th className="px-1.5 py-1 font-semibold">Inputs (t)</th>
                    <th className="px-1.5 py-1 font-semibold text-right">Out u</th>
                    <th className="px-1.5 py-1 font-semibold text-right">CR/u</th>
                    <th className="px-1.5 py-1 font-semibold">Cat</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.recipes ?? []).map((rec) => (
                    <tr key={rec.key} className="border-t border-cyan-900/20 align-top">
                      <td className="px-1.5 py-1 font-mono text-[10px] text-ui-muted">{rec.key}</td>
                      <td className="px-1.5 py-1 text-ui-accent-readable">{rec.name}</td>
                      <td className="px-1.5 py-1 font-mono text-[10px] text-zinc-300">
                        {Object.entries(rec.inputs)
                          .map(([k, v]) => `${k}:${v}`)
                          .join(", ")}
                      </td>
                      <td className="px-1.5 py-1 text-right font-mono tabular-nums">{rec.outputUnits}</td>
                      <td className="px-1.5 py-1 text-right font-mono tabular-nums">{cr(rec.baseValueCrPerUnit)}</td>
                      <td className="px-1.5 py-1 text-ui-muted">{rec.category}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CsPanel>
        </div>
      </div>
    </CsPage>
  );
}

export default function RefineryPage() {
  return (
    <Suspense
      fallback={
        <CsPage>
          <p className="text-sm text-ui-accent-readable">Loading refinery…</p>
        </CsPage>
      }
    >
      <RefineryPageInner />
    </Suspense>
  );
}
