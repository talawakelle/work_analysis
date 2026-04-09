import type { EmployeeProfile } from "../lib/types";

type Props = {
  employee: EmployeeProfile;
};

export default function EmployeeProfileCard({ employee }: Props) {
  return (
    <section className="panel-soft p-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="truncate text-base font-semibold text-slate-800">
            {employee.employee_name}
            <span className="text-sm font-medium text-slate-500"> · {employee.employee_no}</span>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap gap-1.5">
          {employee.primary_division ? <span className="pastel-pill">{employee.primary_division}</span> : null}
          {employee.gender ? <span className="pastel-pill">{employee.gender}</span> : null}
        </div>
      </div>
    </section>
  );
}
