"use client";

import { useState, type ReactNode } from "react";

import {
  glyphAnomaly,
  glyphDayPhase,
  glyphSeason,
  glyphWeather,
} from "@/components/dashboard-world-status-glyphs";
import { PanelExpandButton } from "@/components/panel-expand-button";
import type { ControlSurfaceState } from "@/lib/control-surface-api";

const STORAGE_KEY = "aurnom:dashboard-panel:world-status";

const PANEL_HEADER =
  "flex min-w-0 items-center gap-1 bg-cyan-900/30 px-2 py-1 text-xs font-bold uppercase tracking-widest";

function strVal(v: unknown): string {
  if (v == null || v === "") return "—";
  if (typeof v === "number" && Number.isFinite(v)) return String(v);
  if (typeof v === "string") return v;
  if (typeof v === "boolean") return v ? "yes" : "no";
  return JSON.stringify(v);
}

function SectionCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-zinc-800/70 bg-gradient-to-br from-zinc-900/55 via-zinc-950/80 to-zinc-950 p-2 shadow-[inset_0_1px_0_0_rgba(34,211,238,0.05)]">
      <div className="mb-2 flex items-center gap-2">
        <span
          className="h-1.5 w-1.5 shrink-0 rounded-full bg-cyber-cyan/80 shadow-[0_0_10px_rgba(34,211,238,0.35)]"
          aria-hidden
        />
        <h3 className="text-[10px] font-bold uppercase tracking-[0.14em] text-zinc-400">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function GlyphWrap({ children }: { children: ReactNode }) {
  return (
    <span
      className="inline-flex shrink-0 rounded-md bg-cyan-950/55 p-1 text-cyber-cyan ring-1 ring-cyan-800/35"
      aria-hidden
    >
      {children}
    </span>
  );
}

function StatTile({
  label,
  value,
  glyph,
}: {
  label: string;
  value: unknown;
  glyph?: ReactNode | null;
}) {
  return (
    <div className="flex min-h-[3.5rem] min-w-0 flex-col justify-between gap-1 rounded-md border border-zinc-800/55 bg-zinc-950/45 px-2 py-1.5">
      <span className="text-[9px] font-semibold uppercase tracking-wide text-zinc-500">{label}</span>
      <div className="flex min-w-0 items-center gap-1.5">
        {glyph != null ? <GlyphWrap>{glyph}</GlyphWrap> : null}
        <span className="min-w-0 truncate font-mono text-[11px] leading-tight text-zinc-100">{strVal(value)}</span>
      </div>
    </div>
  );
}

function TimeHero({ iso }: { iso: unknown }) {
  return (
    <div className="mb-2 rounded-md border border-zinc-800/65 bg-black/35 px-2 py-2">
      <div className="mb-1 text-[9px] font-semibold uppercase tracking-wide text-zinc-500">When (IC, UTC)</div>
      <div className="break-all font-mono text-[10px] leading-snug text-zinc-200">{strVal(iso)}</div>
    </div>
  );
}

function VenueBanner({ venueId }: { venueId: string | null }) {
  return (
    <div className="mb-2 flex min-w-0 items-center gap-2 rounded-md border border-cyan-900/40 bg-cyan-950/20 px-2 py-1.5">
      <span className="shrink-0 text-[9px] font-semibold uppercase tracking-wide text-zinc-500">Venue</span>
      <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-cyber-cyan/90">{strVal(venueId)}</span>
    </div>
  );
}

type Props = {
  worldSimulation?: ControlSurfaceState["worldSimulation"] | null;
  roomVenueId?: string | null;
  partyId?: string | null;
  activeInstanceId?: string | null;
  factionStanding?: Record<string, number> | null;
};

/**
 * Read-only IC clock, local venue environment, party/instance ids, faction standings.
 * Rendered below missions/quests in the missions column.
 */
export function DashboardWorldSimulationPanel({
  worldSimulation = null,
  roomVenueId = null,
  partyId = null,
  activeInstanceId = null,
  factionStanding = null,
}: Props) {
  const [open, setOpen] = useState(() => {
    if (typeof window === "undefined") return true;
    try {
      const raw = window.sessionStorage.getItem(STORAGE_KEY);
      return raw == null ? true : raw === "1";
    } catch {
      return true;
    }
  });

  function toggleOpen() {
    setOpen((v) => {
      const next = !v;
      try {
        window.sessionStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      } catch {
        // ignore storage failures
      }
      return next;
    });
  }

  const gc = worldSimulation?.gameClock;
  const byVenue = worldSimulation?.environmentByVenue;
  const localEnv =
    roomVenueId && byVenue && typeof byVenue === "object" && !Array.isArray(byVenue)
      ? (byVenue as Record<string, unknown>)[roomVenueId]
      : null;
  const envObj =
    localEnv && typeof localEnv === "object" && !Array.isArray(localEnv)
      ? (localEnv as Record<string, unknown>)
      : null;

  const standings = factionStanding ? Object.entries(factionStanding).sort(([a], [b]) => a.localeCompare(b)) : [];

  return (
    <section className="mb-1 min-w-0 overflow-hidden rounded-lg border border-cyan-900/45 shadow-lg shadow-black/30">
      <div className={PANEL_HEADER}>
        <span className="min-w-0 truncate text-cyber-cyan">World status</span>
        <PanelExpandButton
          open={open}
          onClick={toggleOpen}
          aria-label={`${open ? "Collapse" : "Expand"} World status`}
          className="ml-auto shrink-0"
        />
      </div>

      {open ? (
        <div className="min-w-0 border-t border-cyan-900/35 bg-zinc-950/95 p-2 text-xs">
          <div className="flex flex-col gap-2">
            <SectionCard title="In-character time">
              {gc && typeof gc === "object" && !Array.isArray(gc) ? (
                <>
                  <TimeHero iso={(gc as Record<string, unknown>).iso_utc} />
                  <div className="grid grid-cols-3 gap-1.5">
                    <StatTile
                      label="Season"
                      value={(gc as Record<string, unknown>).season}
                      glyph={glyphSeason((gc as Record<string, unknown>).season)}
                    />
                    <StatTile
                      label="Phase"
                      value={(gc as Record<string, unknown>).day_phase}
                      glyph={glyphDayPhase((gc as Record<string, unknown>).day_phase)}
                    />
                    <StatTile label="Hour" value={(gc as Record<string, unknown>).hour} />
                  </div>
                </>
              ) : (
                <p className="text-[11px] text-ui-muted">No clock snapshot yet.</p>
              )}
            </SectionCard>

            <SectionCard title="Local environment">
              <VenueBanner venueId={roomVenueId} />
              {envObj ? (
                <>
                  <div className="mb-2 grid grid-cols-2 gap-1.5">
                    <StatTile
                      label="Weather"
                      value={envObj.weather}
                      glyph={glyphWeather(envObj.weather)}
                    />
                    <StatTile label="Pressure" value={envObj.pressure} />
                    <StatTile
                      label="Anomaly"
                      value={envObj.anomaly}
                      glyph={glyphAnomaly(envObj.anomaly)}
                    />
                    <StatTile
                      label="Season bias"
                      value={envObj.season_bias}
                      glyph={glyphSeason(envObj.season_bias)}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    <StatTile label="Perception mod" value={envObj.perception_mod} />
                    <StatTile label="Stealth mod" value={envObj.stealth_mod} />
                  </div>
                </>
              ) : (
                <p className="text-[11px] text-ui-muted">
                  {roomVenueId ? "No environment row for this venue." : "No venue (not in a located room)."}
                </p>
              )}
            </SectionCard>

            <SectionCard title="Party & instance">
              <div className="grid grid-cols-2 gap-1.5">
                <StatTile label="Party id" value={partyId ?? "—"} />
                <StatTile label="Active instance id" value={activeInstanceId ?? "—"} />
              </div>
            </SectionCard>

            <SectionCard title="Faction standing">
              {standings.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {standings.map(([id, val]) => (
                    <div
                      key={id}
                      className="inline-flex min-w-0 max-w-full items-baseline gap-2 rounded-md border border-zinc-700/55 bg-zinc-950/55 px-2 py-1"
                    >
                      <span className="shrink-0 truncate text-[10px] font-semibold uppercase tracking-wide text-zinc-500">
                        {id}
                      </span>
                      <span className="font-mono text-[11px] tabular-nums text-cyber-cyan/95">{strVal(val)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-ui-muted">No standings recorded.</p>
              )}
            </SectionCard>
          </div>
        </div>
      ) : null}
    </section>
  );
}
