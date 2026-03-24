import type { MineSiteDetails } from "@/lib/ui-api";

type Props = {
  site: MineSiteDetails;
};

const TIER_CLASSES: Record<string, { badge: string }> = {
  emerald: {
    badge:
      "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300 dark:bg-emerald-950 dark:text-emerald-400 dark:ring-emerald-700/50",
  },
  amber: {
    badge:
      "bg-amber-100 text-amber-800 ring-1 ring-amber-300 dark:bg-amber-950 dark:text-amber-400 dark:ring-amber-700/50",
  },
  zinc: {
    badge:
      "bg-zinc-100 text-zinc-700 ring-1 ring-zinc-300 dark:bg-zinc-900 dark:text-zinc-400 dark:ring-zinc-700/50",
  },
};

function formatDate(s: string | null) {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleString(undefined, {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return s;
  }
}

function formatComposition(comp: Record<string, number>) {
  const entries = Object.entries(comp);
  if (entries.length === 0) return "—";
  return entries.map(([k, v]) => `${k} ${Math.round(v * 100)}%`).join(", ");
}

function formatInventory(inv: Record<string, number>) {
  const entries = Object.entries(inv);
  if (entries.length === 0) return "—";
  return entries.map(([k, v]) => `${k}: ${v.toFixed(1)} t`).join(" · ");
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded border border-zinc-200 bg-zinc-50 p-2 dark:border-cyan-900/50 dark:bg-zinc-950/80">
      <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-500 dark:text-cyan-400/90">
        {title}
      </h3>
      <div className="flex flex-col gap-1 text-sm">{children}</div>
    </div>
  );
}

function Kv({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-2 text-sm">
      <span className="shrink-0 text-zinc-500 dark:text-cyan-500/80">{label}</span>
      <span className="min-w-0 truncate text-right font-mono text-zinc-800 dark:text-zinc-200">
        {value}
      </span>
    </div>
  );
}

export function MineDetailsPanel({ site }: Props) {
  return (
    <section className="border-b border-zinc-100 px-2 py-2 dark:border-cyan-900/30">
      <h2 className="section-label">Mine Details</h2>
      <div className="mt-1 grid auto-rows-min grid-cols-1 gap-2 sm:grid-cols-2">
        <Card title="Identity">
          <Kv label="Deposit" value={site.key} />
          <Kv label="Location" value={site.location ?? site.roomKey ?? "—"} />
          <Kv label="Room" value={site.roomKey} />
        </Card>

        <Card title="Status">
          <Kv label="Owner" value={site.owner ?? "Unclaimed"} />
          <Kv label="Active" value={site.active ? "Yes" : "No"} />
          <Kv label="Survey" value={`Level ${site.surveyLevel}`} />
        </Card>

        <Card title="Deposit">
          <div className="flex items-center justify-between gap-2">
            <span className="text-zinc-500 dark:text-cyan-500/80">Tier</span>
            <span
              className={`rounded px-1.5 py-0.5 font-mono text-[12px] font-medium ${
                TIER_CLASSES[site.richnessTierCls]?.badge ?? TIER_CLASSES.zinc.badge
              }`}
            >
              {site.richnessTier}
            </span>
          </div>
          <Kv label="Richness" value={`${Math.round(site.richness * 100)}%`} />
          <Kv label="Output" value={`${site.baseOutputTons} t/cycle`} />
          <Kv label="Resources" value={site.resources} />
          <Kv label="Composition" value={formatComposition(site.composition)} />
        </Card>

        <Card title="Hazard">
          <Kv label="Level" value={site.hazardLevel} />
          <Kv label="Rating" value={site.hazardLabel} />
        </Card>

        <Card title="Licensing">
          <Kv label="License" value={`Level ${site.licenseLevel}`} />
          <Kv label="Tax" value={`${(site.taxRate * 100).toFixed(1)}%`} />
        </Card>

        <Card title="Cycle">
          <Kv label="Next cycle" value={formatDate(site.nextCycleAt)} />
          <Kv label="Last processed" value={formatDate(site.lastProcessedAt)} />
          <Kv label="Est. value" value={`${site.estimatedValuePerCycle.toLocaleString()} cr`} />
        </Card>

        <Card title="Depletion">
          <Kv label="Rate" value={`${(site.depletionRate * 100).toFixed(2)}%`} />
          <Kv label="Floor" value={`${Math.round(site.richnessFloor * 100)}%`} />
        </Card>

        <Card title="Storage">
          <Kv label="Used" value={`${site.storageUsed} / ${site.storageCapacity} t`} />
          {Object.keys(site.inventory).length > 0 && (
            <Kv label="Stored" value={formatInventory(site.inventory)} />
          )}
        </Card>

        {site.rig && (
          <Card title="Rig">
            <Kv label="Model" value={site.rig} />
            <Kv label="Rating" value={site.rigRating ?? "—"} />
            <Kv label="Wear" value={site.rigWear != null ? `${site.rigWear}%` : "—"} />
            <Kv label="Operational" value={site.rigOperational ? "Yes" : "No"} />
            <Kv label="Mode" value={site.rigMode ?? "—"} />
          </Card>
        )}

        <Card title="Cycle log">
          {site.cycleLog.length > 0 ? (
            <ul className="space-y-0.5 text-xs text-zinc-600 dark:text-cyan-500/80">
              {site.cycleLog.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          ) : (
            <span className="text-xs text-zinc-500 dark:text-cyan-500/60">—</span>
          )}
        </Card>

        <Card title="Hazard log">
          {site.hazardLog.length > 0 ? (
            <ul className="space-y-0.5 text-xs text-zinc-600 dark:text-cyan-500/80">
              {site.hazardLog.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          ) : (
            <span className="text-xs text-zinc-500 dark:text-cyan-500/60">—</span>
          )}
        </Card>
      </div>
    </section>
  );
}
