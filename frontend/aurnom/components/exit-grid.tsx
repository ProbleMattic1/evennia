import Link from "next/link";

import type { ExitButton } from "@/lib/ui-api";

type Props = {
  exits: ExitButton[];
};

export function ExitGrid({ exits }: Props) {
  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-4">
      <h2 className="mb-3 text-lg font-semibold text-zinc-900">Exits</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {exits.map((exit) => (
          <Link
            key={`${exit.key}-${exit.destination ?? "none"}`}
            href={exit.destination ? `/play?room=${encodeURIComponent(exit.destination)}` : "/play"}
            className="rounded-lg border border-zinc-300 px-4 py-3 text-sm font-medium text-zinc-900 transition hover:bg-zinc-100"
          >
            {exit.label}
          </Link>
        ))}
      </div>
    </section>
  );
}
