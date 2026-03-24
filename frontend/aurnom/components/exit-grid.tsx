import Link from "next/link";

import type { ExitButton } from "@/lib/ui-api";

type Props = {
  exits: ExitButton[];
};

export function ExitGrid({ exits }: Props) {
  return (
    <section className="border-b border-zinc-100 px-2 py-2 dark:border-zinc-800">
      <h2 className="section-label">Exits</h2>
      <ul className="mt-1 flex flex-wrap gap-1">
        {exits.map((exit) => (
          <li key={`${exit.key}-${exit.destination ?? "none"}`}>
            <Link
              href={exit.destination ? `/play?room=${encodeURIComponent(exit.destination)}` : "/play"}
              className="block rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-700 hover:bg-zinc-100 hover:text-zinc-900 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
            >
              {exit.label}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
