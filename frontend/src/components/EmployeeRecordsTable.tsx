import type { DayDetail, DailyRecord } from "../lib/types";

type Props = {
  day: DayDetail | null;
  rows: DailyRecord[];
};

function cleanWorkName(workCode: string | null, workName: string | null) {
  const code = (workCode || "").trim();
  const name = (workName || "").trim();
  if (!name) return "-";
  if (!code) return name;
  return name.toLowerCase() === code.toLowerCase() ? "-" : name;
}

export default function EmployeeRecordsTable({ day, rows }: Props) {
  if (!day) {
    return <div className="table-shell px-5 py-6 text-sm text-slate-500">Select a date box to see that day&apos;s details.</div>;
  }

  return (
    <section className="panel-soft p-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="text-base font-semibold text-slate-800">{day.date}</div>
        {day.kilos > 0 ? <div className="pastel-pill">{day.kilos.toFixed()} kg</div> : null}
        {day.work_code ? <div className="pastel-pill">Code: {day.work_code}</div> : null}
        {cleanWorkName(day.work_code, day.work_name) !== "-" ? (
          <div className="pastel-pill">Name: {cleanWorkName(day.work_code, day.work_name)}</div>
        ) : null}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 xl:grid-cols-4">
        <div className="subtle-card px-3 py-2.5"><div className="eyebrow">Division</div><div className="mt-1 font-medium text-slate-800">{day.division || "-"}</div></div>
        <div className="subtle-card px-3 py-2.5"><div className="eyebrow">Field</div><div className="mt-1 font-medium text-slate-800">{day.field_code || "-"}</div></div>
        <div className="subtle-card px-3 py-2.5"><div className="eyebrow">Gang</div><div className="mt-1 font-medium text-slate-800">{day.gang || "-"}</div></div>
        <div className="subtle-card px-3 py-2.5"><div className="eyebrow">Work Hours</div><div className="mt-1 font-medium text-slate-800">{day.work_hour ?? "-"}</div></div>
        <div className="subtle-card px-3 py-2.5"><div className="eyebrow">Work Code</div><div className="mt-1 font-medium text-slate-800">{day.work_code || "-"}</div></div>
        <div className="subtle-card px-3 py-2.5"><div className="eyebrow">Work Name</div><div className="mt-1 font-medium text-slate-800">{cleanWorkName(day.work_code, day.work_name)}</div></div>
        <div className="subtle-card px-3 py-2.5"><div className="eyebrow">Plantation</div><div className="mt-1 font-medium text-slate-800">{day.plantation || "-"}</div></div>
        <div className="subtle-card px-3 py-2.5"><div className="eyebrow">Crop</div><div className="mt-1 font-medium text-slate-800">{day.crop || "-"}</div></div>
      </div>

      {rows.length > 0 ? (
        <div className="mt-4 table-shell">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-3 py-2.5">Work Code</th>
                  <th className="px-3 py-2.5">Work Name</th>
                  <th className="px-3 py-2.5">Hours</th>
                  <th className="px-3 py-2.5">Kilos</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr key={`${row.date}-${index}`} className="table-row border-t">
                    <td className="px-3 py-2.5 font-medium text-slate-800">{row.work_code || "-"}</td>
                    <td className="px-3 py-2.5 text-slate-700">{cleanWorkName(row.work_code, row.work_name)}</td>
                    <td className="px-3 py-2.5 text-slate-700">{row.work_hour ?? "-"}</td>
                    <td className="px-3 py-2.5 text-slate-700">{row.kilos.toFixed()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </section>
  );
}
