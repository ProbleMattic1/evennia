"use client";

import { useState } from "react";

import { CsButtonLink, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { postReportBug, postReportIdea, postReportPlayer } from "@/lib/ui-api";

type Tab = "bug" | "idea" | "player";

export default function ReportsPage() {
  const [tab, setTab] = useState<Tab>("bug");
  const [target, setTarget] = useState("");
  const [message, setMessage] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setOk(null);
    setBusy(true);
    try {
      if (tab === "bug") {
        const r = await postReportBug({
          target: target.trim() || undefined,
          message: message.trim(),
        });
        setOk(r.message);
      } else if (tab === "idea") {
        const r = await postReportIdea({
          target: target.trim() || undefined,
          message: message.trim(),
        });
        setOk(r.message);
      } else {
        const r = await postReportPlayer({ target: target.trim(), message: message.trim() });
        setOk(r.message);
      }
      setMessage("");
      if (tab === "player") {
        setTarget("");
      }
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(false);
    }
  }

  return (
    <CsPage>
      <CsHeader
        title="Reports"
        subtitle="File bug reports, ideas, or player reports into the same in-game report hubs as telnet commands."
        actions={<CsButtonLink href="/">Back</CsButtonLink>}
      />

      <div className="mb-2 flex flex-wrap gap-2 text-xs">
        {(
          [
            ["bug", "Bug"],
            ["idea", "Idea"],
            ["player", "Player"],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            type="button"
            disabled={busy}
            onClick={() => {
              setTab(k);
              setErr(null);
              setOk(null);
            }}
            className={`rounded border px-2 py-0.5 uppercase tracking-wide ${
              tab === k ? "border-cyber-cyan text-cyber-cyan" : "border-cyan-900/50 text-ui-muted"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <CsPanel title={tab === "bug" ? "Bug" : tab === "idea" ? "Idea" : "Player report"}>
        <form onSubmit={onSubmit} className="space-y-2 text-sm">
          {tab === "player" ? (
            <label className="block">
              <span className="text-ui-muted">Target account or character name</span>
              <input
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                required
                className="mt-0.5 w-full rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1 font-mono text-xs"
              />
            </label>
          ) : (
            <label className="block">
              <span className="text-ui-muted">Optional target (object / location / character)</span>
              <input
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                className="mt-0.5 w-full rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1 font-mono text-xs"
              />
            </label>
          )}
          <label className="block">
            <span className="text-ui-muted">Message</span>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
              rows={6}
              className="mt-0.5 w-full rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1 font-mono text-xs"
            />
          </label>
          {err ? <p className="text-red-600 dark:text-red-400">{err}</p> : null}
          {ok ? <p className="text-emerald-500">{ok}</p> : null}
          <button
            type="submit"
            disabled={busy}
            className="rounded border border-cyber-cyan px-3 py-1 text-xs font-bold uppercase tracking-wide text-cyber-cyan"
          >
            Submit
          </button>
        </form>
      </CsPanel>
    </CsPage>
  );
}
