import Link from "next/link";

type Action = {
  key: string;
  label: string;
  href: string;
};

type Props = {
  actions: Action[];
};

export function ActionGrid({ actions }: Props) {
  return (
    <div className="flex flex-wrap gap-1">
      {actions.map((action) => (
        <Link
          key={action.key}
          href={action.href}
          className="rounded border border-cyan-800/60 px-2 py-1 text-[11px] text-cyan-400 hover:bg-cyan-900/40 hover:text-cyan-300"
        >
          {action.label}
        </Link>
      ))}
    </div>
  );
}
