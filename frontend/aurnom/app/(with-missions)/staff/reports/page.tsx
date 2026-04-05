"use client";

import { useCallback, useEffect, useState } from "react";

import { CsButtonLink, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import type { StaffReportRow } from "@/lib/ui-api";
import { getStaffReportsList, postStaffReportStatus } from "@/lib/ui-api";

export default function StaffReportsPage() {
  const [type, setType] = useState<"bugs" | "ideas" | "players">("bugs");
  const [includeClosed, setIncludeClosed] = useState(false);
  const [rows, setRows] = useState<StaffReportRow[]>([]);
  const [statusTags, setStatusTags] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setErr(null);
    setBusy(true);
    try {
      const data = await getStaffReportsList({ type, includeClosed });
      setRows(data.reports);
      setStatusTags(data.allowedStatusTags);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setRows([]);
    } finally {
      setBusy(false);
    }
  }, [type, includeClosed]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleTag(messageId: number, tag: string, currentlyHas: boolean) {
    setErr(null);
    setBusy(true);
    try {
      await postStaffReportStatus({ messageId, tag, add: !currentlyHas });
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <CsPage>
      <CsHeader
        title="Manage reports"
        subtitle="Admin-only; mirrors the in-game manage reports menu (status tags on report messages)."
        actions={<CsButtonLink href="/">Back</CsButtonLink>}
      />

      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
        <span className="text-ui-muted">Type:</span>
        {(["bugs", "ideas", "players"] as const).map((t) => (
          <button
            key={t}
            type="button"
            disabled={busy}
            onClick={() => setType(t)}
            className={`rounded border px-2 py-0.5 uppercase tracking-wide ${
              type === t ? "border-cyber-cyan text-cyber-cyan" : "border-cyan-900/50 text-ui-muted"
            }`}
          >
            {t}
          </button>
        ))}
        <label className="ml-2 flex items-center gap-1 text-ui-muted">
          <input
            type="checkbox"
            checked={includeClosed}
            onChange={(e) => setIncludeClosed(e.target.checked)}
            disabled={busy}
          />
          Include closed
        </label>
      </div>

      {err ? <p className="mb-2 text-sm text-red-600 dark:text-red-400">{err}</p> : null}

      <CsPanel title="Reports">
        {rows.length === 0 ? (
          <p className="text-sm text-ui-muted">No reports.</p>
        ) : (
          <div className="overflow-x-auto text-xs">
            <table className="w-full min-w-[48rem] border-collapse text-left">
              <thead>
                <tr className="border-b border-cyan-900/50 bg-zinc-950/80">
                  <th className="px-2 py-1.5 font-medium text-cyber-cyan">When</th>
                  <th className="px-2 py-1.5 font-medium text-cyber-cyan">From</th>
                  <th className="px-2 py-1.5 font-medium text-cyber-cyan">Message</th>
                  <th className="px-2 py-1.5 font-medium text-cyber-cyan">Tags</th>
                  <th className="px-2 py-1.5 font-medium text-cyber-cyan">Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-b border-cyan-950/60 align-top">
                    <td className="whitespace-nowrap px-2 py-1 font-mono text-ui-muted">{r.dateCreated ?? "—"}</td>
                    <td className="max-w-[10rem] px-2 py-1 font-mono text-ui-muted">{r.senders.join(", ")}</td>
                    <td className="max-w-xl px-2 py-1 whitespace-pre-wrap break-words">{r.message}</td>
                    <td className="px-2 py-1 font-mono text-ui-muted">{r.tags.join(", ")}</td>
                    <td className="px-2 py-1">
                      <div className="flex flex-col gap-1">
                        {statusTags.map((tag) => {
                          const on = r.tags.includes(tag);
                          return (
                            <button
                              key={tag}
                              type="button"
                              disabled={busy}
                              onClick={() => void toggleTag(r.id, tag, on)}
                              className={`rounded border px-1.5 py-0.5 text-left ${
                                on ? "border-emerald-700 text-emerald-400" : "border-cyan-900/50 text-ui-muted"
                              }`}
                            >
                              {on ? "✓ " : "○ "}
                              {tag}
                            </button>
                          );
                        })}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CsPanel>
    </CsPage>
  );
}
