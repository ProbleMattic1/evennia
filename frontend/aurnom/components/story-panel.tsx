import type { StoryLine } from "@/lib/ui-api";

type Props = {
  /** Omit when the parent panel already shows the same heading (e.g. CsPanel). */
  title?: string;
  lines: StoryLine[];
  /** Tighter box; avoids empty terminal feel when few lines (Play / two-column layouts). */
  compact?: boolean;
  /** Grow to fill a flex parent; use with `compact` typography (no max-height cap). */
  flexFill?: boolean;
};

export function StoryPanel({ title, lines, compact, flexFill }: Props) {
  const boxClass = flexFill
    ? "min-h-0 flex-1 overflow-y-auto bg-zinc-950/80 p-2 font-mono text-xs leading-5 text-ui-soft"
    : compact
      ? "max-h-[min(200px,40vh)] min-h-0 overflow-y-auto border border-cyan-900/40 bg-zinc-950/80 p-2 font-mono text-xs leading-5 text-ui-soft"
      : "max-h-[min(320px,50vh)] min-h-[200px] overflow-y-auto border border-cyan-900/40 bg-zinc-950/80 p-2 font-mono text-xs leading-5 text-ui-soft";

  return (
    <div className={flexFill ? "flex min-h-0 flex-1 flex-col" : undefined}>
      {title ? (
        <div className="mb-1 text-xs font-bold uppercase tracking-widest text-cyber-cyan">{title}</div>
      ) : null}
      <div className={boxClass}>
        {lines.map((line) => (
          <p
            key={line.id}
            className={
              line.kind === "title"
                ? "mb-2 text-xs font-semibold text-amber-300"
                : line.kind === "system"
                  ? "mb-1.5 text-xs text-cyber-cyan"
                  : "mb-1.5 text-xs text-ui-soft"
            }
          >
            {line.text}
          </p>
        ))}
      </div>
    </div>
  );
}
