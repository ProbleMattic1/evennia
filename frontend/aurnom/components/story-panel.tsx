import type { StoryLine } from "@/lib/ui-api";

type Props = {
  /** Omit when the parent panel already shows the same heading (e.g. CsPanel). */
  title?: string;
  lines: StoryLine[];
  /** Tighter box; avoids empty terminal feel when few lines (Play / two-column layouts). */
  compact?: boolean;
};

export function StoryPanel({ title, lines, compact }: Props) {
  const boxClass = compact
    ? "max-h-[min(200px,40vh)] min-h-0 overflow-y-auto border border-cyan-900/40 bg-zinc-950/80 p-2 font-mono text-[11px] leading-5 text-zinc-200"
    : "max-h-[min(320px,50vh)] min-h-[200px] overflow-y-auto border border-cyan-900/40 bg-zinc-950/80 p-2 font-mono text-[11px] leading-5 text-zinc-200";

  return (
    <div>
      {title ? (
        <div className="mb-1 text-[10px] font-bold uppercase tracking-widest text-cyan-300">{title}</div>
      ) : null}
      <div className={boxClass}>
        {lines.map((line) => (
          <p
            key={line.id}
            className={
              line.kind === "title"
                ? "mb-2 text-[11px] font-semibold text-amber-300"
                : line.kind === "system"
                  ? "mb-1.5 text-[11px] text-cyan-400"
                  : "mb-1.5 text-[11px] text-zinc-200"
            }
          >
            {line.text}
          </p>
        ))}
      </div>
    </div>
  );
}
