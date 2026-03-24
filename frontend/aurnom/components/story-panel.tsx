import type { StoryLine } from "@/lib/ui-api";

type Props = {
  title: string;
  lines: StoryLine[];
};

export function StoryPanel({ title, lines }: Props) {
  return (
    <section className="border-b border-zinc-100 px-2 py-2 dark:border-cyan-900/30">
      <h2 className="section-label">{title}</h2>
      <div className="mt-1 h-[280px] overflow-y-auto rounded border border-zinc-200 bg-zinc-50 p-2 font-mono text-sm leading-5 text-zinc-800 dark:border-cyan-900/50 dark:bg-zinc-950/80 dark:text-zinc-200">
        {lines.map((line) => (
          <p
            key={line.id}
            className={
              line.kind === "title"
                ? "mb-2 text-sm font-semibold text-amber-700 dark:text-amber-300"
                : line.kind === "system"
                  ? "mb-1.5 text-sm text-sky-700 dark:text-cyan-400"
                  : "mb-1.5 text-sm text-zinc-800 dark:text-zinc-200"
            }
          >
            {line.text}
          </p>
        ))}
      </div>
    </section>
  );
}
