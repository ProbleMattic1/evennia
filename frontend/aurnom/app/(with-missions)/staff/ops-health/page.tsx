"use client";

import { useCallback, useEffect, useState } from "react";

import { CsButtonLink, CsHeader, CsPage, CsPanel } from "@/components/cs-page-primitives";
import {
  getManufacturingOpsHealth,
  getPropertyOpsHealth,
  type ManufacturingOpsHealthResponse,
  type PropertyOpsHealthResponse,
} from "@/lib/ui-api";

export default function StaffOpsHealthPage() {
  const [prop, setProp] = useState<PropertyOpsHealthResponse | null>(null);
  const [mfg, setMfg] = useState<ManufacturingOpsHealthResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      setProp(await getPropertyOpsHealth());
    } catch (e) {
      setProp({
        ok: false,
        message: e instanceof Error ? e.message : "Property ops health failed",
      });
    }
    try {
      setMfg(await getManufacturingOpsHealth());
    } catch (e) {
      setMfg({
        ok: false,
        message: e instanceof Error ? e.message : "Manufacturing ops health failed",
      });
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <CsPage>
      <CsHeader
        title="Engine health"
        subtitle="Staff-only observability"
        actions={
          <CsButtonLink href="/" variant="dashboard">
            Back to dashboard
          </CsButtonLink>
        }
      />
      <div className="p-1.5">
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="mb-2 rounded border border-cyan-800/60 px-2 py-1 text-xs text-cyber-cyan hover:bg-cyan-950/40 disabled:opacity-50"
        >
          {loading ? "Loading…" : "Refresh"}
        </button>
        {err ? (
          <p className="mb-2 font-mono text-sm text-red-400" role="alert">
            {err}
          </p>
        ) : null}

        <CsPanel title="Property operations">
          {loading ? (
            <p className="text-ui-muted">…</p>
          ) : prop?.ok ? (
            <ul className="mt-1 space-y-1 font-mono text-xs text-foreground">
              <li>engineActive: {String(prop.engineActive)}</li>
              <li>engineInterval: {prop.engineInterval ?? "—"}</li>
              <li>eventsEngineActive: {String(prop.eventsEngineActive)}</li>
              <li>eventsEngineInterval: {prop.eventsEngineInterval ?? "—"}</li>
              <li>registeredHoldings: {prop.registeredHoldings ?? "—"}</li>
            </ul>
          ) : (
            <p className="font-mono text-xs text-red-400">{prop?.message ?? "No data"}</p>
          )}
        </CsPanel>

        <CsPanel title="Manufacturing">
          {loading ? (
            <p className="text-ui-muted">…</p>
          ) : mfg?.ok ? (
            <ul className="mt-1 space-y-1 font-mono text-xs text-foreground">
              <li>engineKey: {mfg.engineKey ?? "—"}</li>
              <li>registryHoldingCount: {mfg.registryHoldingCount ?? "—"}</li>
              <li>registryWorkshopIdsTotal: {mfg.registryWorkshopIdsTotal ?? "—"}</li>
            </ul>
          ) : (
            <p className="font-mono text-xs text-red-400">{mfg?.message ?? "No data"}</p>
          )}
        </CsPanel>
      </div>
    </CsPage>
  );
}
