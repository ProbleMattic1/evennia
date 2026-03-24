import type { MineSiteDetails } from "@/lib/ui-api";

type Props = {
  site: MineSiteDetails;
};

function Kv({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-2 text-sm">
      <span className="shrink-0 text-zinc-500 dark:text-zinc-400">{label}:</span>
      <span className="text-zinc-800 dark:text-zinc-200">{value}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
        {title}
      </h3>
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}

export function MineDetailsPanel({ site }: Props) {
  return (
    <section className="border-b border-zinc-100 px-2 py-2 dark:border-zinc-800">
      <h2 className="section-label">Mine Details</h2>
      <div className="mt-1 max-h-[400px] overflow-y-auto rounded border border-zinc-200 bg-zinc-50 p-2 font-mono text-sm leading-5 text-zinc-800 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-200">
        <Section title="Identity">
          <Kv label="id" value={site.id} />
          <Kv label="key" value={site.key} />
          <Kv label="siteKey" value={site.siteKey} />
          <Kv label="roomKey" value={site.roomKey} />
          <Kv label="location" value={site.location ?? "—"} />
        </Section>
        <Section title="Status">
          <Kv label="isClaimed" value={String(site.isClaimed)} />
          <Kv label="owner" value={site.owner ?? "—"} />
          <Kv label="active" value={String(site.active)} />
          <Kv label="surveyLevel" value={site.surveyLevel} />
        </Section>
        <Section title="Deposit">
          <Kv label="richness" value={site.richness} />
          <Kv label="richnessTier" value={site.richnessTier} />
          <Kv label="richnessTierCls" value={site.richnessTierCls} />
          <Kv label="baseOutputTons" value={site.baseOutputTons} />
          <Kv label="resources" value={site.resources} />
          <Kv label="composition" value={JSON.stringify(site.composition)} />
        </Section>
        <Section title="Depletion">
          <Kv label="depletionRate" value={site.depletionRate} />
          <Kv label="richnessFloor" value={site.richnessFloor} />
        </Section>
        <Section title="Licensing">
          <Kv label="licenseLevel" value={site.licenseLevel} />
          <Kv label="taxRate" value={site.taxRate} />
        </Section>
        <Section title="Hazard">
          <Kv label="hazardLevel" value={site.hazardLevel} />
          <Kv label="hazardLabel" value={site.hazardLabel} />
        </Section>
        <Section title="Cycle">
          <Kv label="nextCycleAt" value={site.nextCycleAt ?? "—"} />
          <Kv label="lastProcessedAt" value={site.lastProcessedAt ?? "—"} />
          <Kv label="estimatedValuePerCycle" value={`${site.estimatedValuePerCycle.toLocaleString()} cr`} />
        </Section>
        <Section title="Rig">
          <Kv label="rig" value={site.rig ?? "—"} />
          <Kv label="rigRating" value={site.rigRating ?? "—"} />
          <Kv label="rigWear" value={site.rigWear != null ? `${site.rigWear}%` : "—"} />
          <Kv label="rigOperational" value={site.rigOperational != null ? String(site.rigOperational) : "—"} />
          <Kv label="rigMode" value={site.rigMode ?? "—"} />
          <Kv label="rigPowerLevel" value={site.rigPowerLevel ?? "—"} />
          <Kv label="rigTargetFamily" value={site.rigTargetFamily ?? "—"} />
          <Kv label="rigPurityCutoff" value={site.rigPurityCutoff ?? "—"} />
          <Kv label="rigMaintenanceLevel" value={site.rigMaintenanceLevel ?? "—"} />
        </Section>
        <Section title="Storage">
          <Kv label="storageUsed" value={`${site.storageUsed} t`} />
          <Kv label="storageCapacity" value={`${site.storageCapacity} t`} />
          <Kv label="inventory" value={JSON.stringify(site.inventory)} />
        </Section>
        <Section title="cycleLog">
          {site.cycleLog.length > 0 ? (
            site.cycleLog.map((line, i) => (
              <div key={i} className="text-xs text-zinc-600 dark:text-zinc-400">
                {line}
              </div>
            ))
          ) : (
            <span className="text-zinc-500 dark:text-zinc-600">—</span>
          )}
        </Section>
        <Section title="hazardLog">
          {site.hazardLog.length > 0 ? (
            site.hazardLog.map((line, i) => (
              <div key={i} className="text-xs text-zinc-600 dark:text-zinc-400">
                {line}
              </div>
            ))
          ) : (
            <span className="text-zinc-500 dark:text-zinc-600">—</span>
          )}
        </Section>
      </div>
    </section>
  );
}
