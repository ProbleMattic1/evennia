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
    <section className="border-b border-zinc-100 px-2 py-2 dark:border-cyan-900/30">
      <h2 className="section-label">Actions</h2>
      <ul className="mt-1 flex flex-wrap gap-1">
        {actions.map((action) => (
          <li key={action.key}>
            <Link
              href={action.href}
              className="block rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-700 hover:bg-zinc-100 hover:text-zinc-900 dark:border-cyan-700/50 dark:bg-cyan-950/40 dark:text-cyan-400 dark:hover:bg-cyan-900/50 dark:hover:text-cyan-300"
            >
              {action.label}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
