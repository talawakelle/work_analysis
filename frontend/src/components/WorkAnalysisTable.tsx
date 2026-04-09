import type { WorkAnalysisRow } from "../lib/types";

type Props = {
  rows: WorkAnalysisRow[];
  onSelectEmployee?: (row: WorkAnalysisRow) => void;
  showEstate?: boolean;
};

const rowClassMap: Record<WorkAnalysisRow["row_color"], string> = {
  "light-green": "status-green",
  red: "status-red",
  amber: "status-amber",
  neutral: "status-neutral",
};

export default function WorkAnalysisTable({ rows, onSelectEmployee, showEstate = false }: Props) {
  if (!rows.length) {
    return <div className="table-shell px-5 py-6 text-sm text-slate-500">No employees found for this filter.</div>;
  }

  return (
    <div className="table-shell">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="table-head">
            <tr>
              <th className="px-2.5 py-2.5">Employee No</th>
              <th className="px-2.5 py-2.5">Employee</th>
              {showEstate ? <th className="px-2.5 py-2.5">Estate</th> : null}
              <th className="px-2.5 py-2.5">Division</th>
              <th className="px-2.5 py-2.5">Type</th>
              <th className="px-2.5 py-2.5">Kilos</th>
              <th className="px-2.5 py-2.5">Days</th>
              <th className="px-2.5 py-2.5">Avg/Day</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.employee_id}
                className={`table-row border-t ${rowClassMap[row.row_color]} ${onSelectEmployee ? "cursor-pointer hover:brightness-[0.99]" : ""}`}
                onClick={() => onSelectEmployee?.(row)}
              >
                <td className="px-2.5 py-2.5 text-slate-700">{row.employee_no}</td>
                <td className="px-2.5 py-2.5 font-medium text-slate-800">{row.employee_name}</td>
                {showEstate ? <td className="px-2.5 py-2.5 text-slate-600">{row.estate}</td> : null}
                <td className="px-2.5 py-2.5 text-slate-600">{row.division || "-"}</td>
                <td className="px-2.5 py-2.5 text-slate-600">{row.employment_type || "-"}</td>
                <td className="px-2.5 py-2.5 text-slate-700">{row.total_kilos.toFixed(2)}</td>
                <td className="px-2.5 py-2.5 text-slate-700">{row.total_days}</td>
                <td className="px-2.5 py-2.5 text-slate-700">{row.avg_kilos_per_day.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
