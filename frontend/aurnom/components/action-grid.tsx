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
    <section className="rounded-xl border border-zinc-200 bg-white p-4">
      <h2 className="mb-3 text-lg font-semibold text-zinc-900">Actions</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {actions.map((action) => (
          <Link
            key={action.key}
            href={action.href}
            className="rounded-lg bg-zinc-900 px-4 py-3 text-sm font-medium text-white transition hover:bg-zinc-700"
          >
            {action.label}
          </Link>
        ))}
      </div>
    </section>
  );
}
