import Link from "next/link";

import type { ExitButton } from "@/lib/ui-api";

type Props = {
  exits: ExitButton[];
};

export function ExitGrid({ exits }: Props) {
  return (
    <section className="border-b border-zinc-100 px-2 py-2 dark:border-cyan-900/30">
      <h2 className="section-label">Exits</h2>
      <ul className="mt-1 flex flex-wrap gap-1">
        {exits.map((exit) => (
          <li key={`${exit.key}-${exit.destination ?? "none"}`}>
            <Link
              href={exit.destination ? `/play?room=${encodeURIComponent(exit.destination)}` : "/play"}
              className="block rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-700 hover:bg-zinc-100 hover:text-zinc-900 dark:border-cyan-700/50 dark:text-cyan-400 dark:hover:bg-cyan-950/40 dark:hover:text-cyan-300"
            >
              {exit.label}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
