"use client";

import { useState } from "react";

import { CsButtonLink, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import { postPlayRoll } from "@/lib/ui-api";

export default function RollPage() {
  const [expression, setExpression] = useState("2d6");
  const [visibility, setVisibility] = useState<"public" | "secret">("secret");
  const [result, setResult] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onRoll(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    setResult(null);
    try {
      const out = await postPlayRoll({ expression: expression.trim(), visibility });
      setResult(out.result);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(false);
    }
  }

  return (
    <CsPage>
      <CsHeader
        title="Dice"
        subtitle="Uses the same dice syntax as the in-game roll command (e.g. 1d20+3, 2d6+1 > 7)."
        actions={<CsButtonLink href="/">Back</CsButtonLink>}
      />
      <CsPanel title="Roll">
        <form onSubmit={onRoll} className="space-y-2 text-sm">
          <label className="block">
            <span className="text-ui-muted">Expression</span>
            <input
              value={expression}
              onChange={(e) => setExpression(e.target.value)}
              className="mt-0.5 w-full rounded border border-cyan-900/50 bg-zinc-950 px-2 py-1 font-mono text-sm"
            />
          </label>
          <fieldset className="text-ui-muted">
            <legend className="mb-1 text-xs uppercase tracking-wide">Visibility</legend>
            <label className="mr-4">
              <input
                type="radio"
                name="vis"
                checked={visibility === "secret"}
                onChange={() => setVisibility("secret")}
              />{" "}
              Secret (only you see the result)
            </label>
            <label>
              <input
                type="radio"
                name="vis"
                checked={visibility === "public"}
                onChange={() => setVisibility("public")}
              />{" "}
              Public (room sees the roll line)
            </label>
          </fieldset>
          {err ? <p className="text-red-600 dark:text-red-400">{err}</p> : null}
          {result != null ? (
            <p className="font-mono text-lg tabular-nums text-cyber-cyan">
              Result: <span className="text-foreground">{result}</span>
            </p>
          ) : null}
          <button
            type="submit"
            disabled={busy}
            className="rounded border border-cyber-cyan px-3 py-1 text-xs font-bold uppercase tracking-wide text-cyber-cyan"
          >
            Roll
          </button>
        </form>
      </CsPanel>
    </CsPage>
  );
}
