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
    <section className="border-b border-zinc-100 px-2 py-2 dark:border-zinc-800">
      <h2 className="section-label">Actions</h2>
      <ul className="mt-1 flex flex-wrap gap-1">
        {actions.map((action) => (
          <li key={action.key}>
            <Link
              href={action.href}
              className="block rounded border border-zinc-300 px-2 py-1 text-sm text-zinc-700 hover:bg-zinc-100 hover:text-zinc-900 dark:border-zinc-600 dark:bg-zinc-800 dark:text-white dark:hover:bg-zinc-700"
            >
              {action.label}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
