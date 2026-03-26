import Link from "next/link";

import type { ExitButton } from "@/lib/ui-api";

type Props = {
  exits: ExitButton[];
};

export function ExitGrid({ exits }: Props) {
  return (
    <div className="flex flex-wrap gap-1">
      {exits.map((exit) => (
        <Link
          key={`${exit.key}-${exit.destination ?? "none"}`}
          href={exit.destination ? `/play?room=${encodeURIComponent(exit.destination)}` : "/play"}
          className="rounded border border-cyan-800/60 px-2 py-1 text-[11px] text-cyan-400 hover:bg-cyan-900/40 hover:text-cyan-300"
        >
          {exit.label}
        </Link>
      ))}
    </div>
  );
}
