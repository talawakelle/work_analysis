import type { WorkCodeSummaryItem } from "../lib/types";

type Props = {
  items: WorkCodeSummaryItem[];
};

export default function BadgeList({ items }: Props) {
  if (!items.length) {
    return <div className="badge-card p-4 text-sm text-slate-500">No work code summary yet.</div>;
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <div key={`${item.work_code}-${item.work_name}`} className="badge-card p-4">
          <div className="text-sm font-semibold text-slate-800">{item.work_code}</div>
          <div className="text-sm text-slate-600">{item.work_name}</div>
          <div className="mt-2 text-xs text-slate-500">
            {item.days} days · {item.records} records
          </div>
        </div>
      ))}
    </div>
  );
}
