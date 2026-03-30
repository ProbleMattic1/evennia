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
          className="rounded border border-cyan-800/60 px-2 py-1 text-xs text-cyber-cyan hover:bg-cyan-900/40 hover:text-cyber-cyan"
        >
          {action.label}
        </Link>
      ))}
    </div>
  );
}
