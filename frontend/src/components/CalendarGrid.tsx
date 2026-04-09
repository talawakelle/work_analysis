import type { CalendarDay } from "../lib/types";

type Props = {
  month: string;
  days: CalendarDay[];
  selectedDate?: string | null;
  onSelect: (day: CalendarDay) => void;
};

const colorMap: Record<CalendarDay["color"], string> = {
  green: "status-green",
  red: "status-red",
  neutral: "status-neutral",
};

const weekdayLabels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function dayNumber(dateValue: string) {
  return dateValue.split("-").pop() ?? dateValue;
}

function secondaryText(day: CalendarDay) {
  const kilosText = day.kilos > 0 ? `${Math.round(day.kilos)}kg` : "";
  const rawCode = (day.work_code || "").trim();

  const codes = rawCode
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  const nonPluckingCodes = codes.filter((code) => {
    const normalized = code.toLowerCase();
    return normalized !== "plucker" && normalized !== "plk" && normalized !== "pkg" && normalized !== "opl";
  });

  const codeText = nonPluckingCodes.join(", ");

  if (kilosText && codeText) return `${kilosText}, ${codeText}`;
  if (kilosText) return kilosText;
  if (codeText) return codeText;

  return "";
}

function buildCalendarCells(month: string, days: CalendarDay[]) {
  if (!month) return [];

  const [year, monthIndex] = month.split("-").map(Number);
  const firstDay = new Date(year, monthIndex - 1, 1);
  const totalDays = new Date(year, monthIndex, 0).getDate();

  const leadingBlanks = (firstDay.getDay() + 6) % 7;
  const dayMap = new Map(days.map((day) => [day.date, day]));

  const cells: Array<{ kind: "blank" } | { kind: "day"; day: CalendarDay; isPlaceholder: boolean }> = [];

  for (let i = 0; i < leadingBlanks; i += 1) {
    cells.push({ kind: "blank" });
  }

  for (let day = 1; day <= totalDays; day += 1) {
    const date = `${month}-${String(day).padStart(2, "0")}`;
    const existing = dayMap.get(date);

    if (existing) {
      cells.push({ kind: "day", day: existing, isPlaceholder: false });
      continue;
    }

    cells.push({
      kind: "day",
      isPlaceholder: true,
      day: {
        date,
        kilos: 0,
        worked: false,
        work_hour: null,
        work_code: null,
        work_name: null,
        employment_type: null,
        division: null,
        field_code: null,
        gang: null,
        plantation: null,
        crop: null,
        hectare: null,
        gender: null,
        color: "neutral",
      },
    });
  }

  return cells;
}

export default function CalendarGrid({ month, days, selectedDate, onSelect }: Props) {
  const cells = buildCalendarCells(month, days);

  return (
    <section className="panel-soft p-3">
      <div className="grid grid-cols-7 gap-1.5 sm:gap-2">
        {weekdayLabels.map((label) => (
          <div
            key={label}
            className="rounded-xl bg-[#f2f4ee] px-1.5 py-1.5 text-center text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500"
          >
            {label}
          </div>
        ))}

        {cells.map((cell, index) => {
          if (cell.kind === "blank") {
            return (
              <div
                key={`blank-${index}`}
                className="min-h-[64px] rounded-2xl border border-dashed border-[#dbe4d8] bg-transparent sm:min-h-[78px]"
              />
            );
          }

          const info = secondaryText(cell.day);
          const isSelected = selectedDate === cell.day.date;
          const isClickable = !cell.isPlaceholder && (cell.day.kilos > 0 || !!cell.day.work_code || cell.day.worked);

          return (
            <button
              key={cell.day.date}
              type="button"
              onClick={() => {
                if (isClickable) onSelect(cell.day);
              }}
              className={`min-h-[64px] rounded-2xl border px-1.5 py-1.5 text-center shadow-sm transition sm:min-h-[78px] sm:px-2 sm:py-2 ${
                cell.isPlaceholder
                  ? "border-[#e3e9df] bg-[#f8faf6] text-slate-300 shadow-none"
                  : `${colorMap[cell.day.color]} ${isClickable ? "hover:brightness-[0.99]" : ""}`
              } ${isSelected ? "ring-2 ring-[#7aa38b]" : ""} ${!isClickable ? "cursor-default" : ""}`}
            >
              <div className={`text-xs font-semibold ${cell.isPlaceholder ? "text-slate-300" : "text-slate-500"}`}>
                {dayNumber(cell.day.date)}
              </div>
              <div
                className={`mt-2 text-[13px] font-bold leading-tight ${cell.isPlaceholder ? "text-slate-300" : "text-slate-800"}`}
              >
                {info || "\u00A0"}
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}