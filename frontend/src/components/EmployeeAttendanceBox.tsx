
import type { AttendanceSummary } from "../lib/types";

type Props = {
  attendance: AttendanceSummary;
};

export default function EmployeeAttendanceBox({ attendance }: Props) {
  return (
    <section className="panel-soft p-3">
      <div className="text-sm font-semibold text-slate-800">Attendance Summary</div>
      <div className="mt-2 grid grid-cols-3 gap-2">
        <div className="subtle-card px-3 py-2.5">
          <div className="eyebrow">Present Days</div>
          <div className="mt-1 text-lg font-semibold text-slate-800 sm:text-2xl">{attendance.present_days}</div>
        </div>
        <div className="subtle-card px-3 py-2.5">
          <div className="eyebrow">Absent Days</div>
          <div className="mt-1 text-lg font-semibold text-slate-800 sm:text-2xl">{attendance.absent_days}</div>
        </div>
        <div className="subtle-card px-3 py-2.5">
          <div className="eyebrow">Month Days</div>
          <div className="mt-1 text-lg font-semibold text-slate-800 sm:text-2xl">{attendance.total_days}</div>
        </div>
      </div>
    </section>
  );
}
