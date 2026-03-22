import type { StoryLine } from "@/lib/ui-api";

type Props = {
  title: string;
  lines: StoryLine[];
};

export function StoryPanel({ title, lines }: Props) {
  return (
    <section className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 text-zinc-100">
      <h2 className="mb-3 text-lg font-semibold">{title}</h2>
      <div className="h-[420px] overflow-y-auto rounded-lg bg-black/40 p-4 font-mono text-sm leading-6">
        {lines.map((line) => (
          <p
            key={line.id}
            className={
              line.kind === "title"
                ? "mb-3 text-base font-semibold text-amber-300"
                : line.kind === "system"
                  ? "mb-2 text-sky-300"
                  : "mb-2 text-zinc-200"
            }
          >
            {line.text}
          </p>
        ))}
      </div>
    </section>
  );
}
