import type { SummaryCard } from "../lib/types";

type Props = {
  items: SummaryCard[];
};

export default function SummaryCards({ items }: Props) {
  if (!items.length) return null;

  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
      {items.map((item) => (
        <div key={item.label} className="panel-soft min-w-0 px-3 py-3 shadow-sm">
          <div className="truncate text-[10px] uppercase tracking-[0.18em] text-slate-500">{item.label}</div>
          <div className="mt-1 truncate text-lg font-semibold leading-none text-slate-800 sm:text-xl">
            {item.value}
          </div>
        </div>
      ))}
    </div>
  );
}
