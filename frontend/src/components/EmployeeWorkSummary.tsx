import type { DailyRecord, EmployeeWorkSummaryItem, PluckingKiloShare } from "../lib/types";

type Props = {
  items: EmployeeWorkSummaryItem[];
  records: DailyRecord[];
  pluckingShare: PluckingKiloShare;
  employeeName: string;
};

const SLICE_COLORS = [
  "#86b39a",
  "#d9b88f",
  "#b8c5dd",
  "#d8a4a8",
  "#c3d0a4",
  "#9dbec6",
  "#d8c59d",
  "#bba7cf",
];

function polarToCartesian(cx: number, cy: number, radius: number, angleDeg: number) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(angleRad),
    y: cy + radius * Math.sin(angleRad),
  };
}

function describeArc(cx: number, cy: number, radius: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(cx, cy, radius, endAngle);
  const end = polarToCartesian(cx, cy, radius, startAngle);
  const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;
  return ["M", start.x, start.y, "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y].join(" ");
}

function formatWorkLabel(item: EmployeeWorkSummaryItem) {
  const code = item.work_code?.trim() ?? "";
  const name = item.work_name?.trim() ?? "";

  if (!code && !name) return "-";
  if (!name) return code;
  if (!code) return name;
  if (name.toLowerCase() === code.toLowerCase()) return code;

  return `${code} — ${name}`;
}

function formatCompactNumber(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatDaysLabel(value: number) {
  const display = formatCompactNumber(value);
  return `${display} ${Number(value) === 1 ? "day" : "days"}`;
}

function buildChartData(items: EmployeeWorkSummaryItem[]) {
  const chartItems = [...items].sort((a, b) => b.days - a.days || b.kilos - a.kilos);
  if (chartItems.length <= 6) return chartItems;

  const kept = chartItems.slice(0, 5);
  const other = chartItems.slice(5);

  return [
    ...kept,
    {
      work_code: "OTH",
      work_name: "Other Work",
      days: Number(other.reduce((sum, item) => sum + item.days, 0).toFixed(2)),
      kilos: Number(other.reduce((sum, item) => sum + item.kilos, 0).toFixed(2)),
    },
  ];
}

function buildDayShareData(records: DailyRecord[]): EmployeeWorkSummaryItem[] {
  const byDate = new Map<string, DailyRecord[]>();

  for (const record of records) {
    const list = byDate.get(record.date) ?? [];
    list.push(record);
    byDate.set(record.date, list);
  }

  const grouped = new Map<string, EmployeeWorkSummaryItem>();

  for (const [, dayRecords] of byDate) {
    const uniqueWorks = new Map<string, { work_code: string; work_name: string; kilos: number }>();

    for (const record of dayRecords) {
      const workCode = (record.work_code || "").trim() || "Unknown";
      const rawWorkName = (record.work_name || "").trim();
      const workName = rawWorkName && rawWorkName.toLowerCase() !== workCode.toLowerCase() ? rawWorkName : "";
      const key = `${workCode}|||${workName}`;

      const current = uniqueWorks.get(key) ?? {
        work_code: workCode,
        work_name: workName,
        kilos: 0,
      };

      current.kilos += Number(record.kilos || 0);
      uniqueWorks.set(key, current);
    }

    const workList = Array.from(uniqueWorks.values());
    const share = workList.length > 0 ? 1 / workList.length : 0;

    for (const work of workList) {
      const key = `${work.work_code}|||${work.work_name}`;
      const current = grouped.get(key) ?? {
        work_code: work.work_code,
        work_name: work.work_name,
        days: 0,
        kilos: 0,
      };

      current.days += share;
      current.kilos += work.kilos;
      grouped.set(key, current);
    }
  }

  return Array.from(grouped.values())
    .map((item) => ({
      ...item,
      days: Number(item.days.toFixed(2)),
      kilos: Number(item.kilos.toFixed(2)),
    }))
    .sort((a, b) => b.days - a.days || b.kilos - a.kilos);
}

function DonutChart({
  title,
  subtitle,
  items,
  valueKey,
  centerLabel,
  centerValue,
  suffix,
}: {
  title: string;
  subtitle?: string;
  items: EmployeeWorkSummaryItem[];
  valueKey: "days" | "kilos";
  centerLabel: string;
  centerValue: string;
  suffix: string;
}) {
  const filtered = items.filter((item) => item[valueKey] > 0);
  const total = filtered.reduce((sum, item) => sum + item[valueKey], 0);
  let currentAngle = 0;

  return (
    <div className="subtle-card px-3 py-3">
      <div className="text-sm font-semibold text-slate-800">{title}</div>
      {subtitle ? <div className="mt-1 text-xs text-slate-500">{subtitle}</div> : null}

      {total > 0 ? (
        <>
          <div className="mt-3 flex justify-center">
            <svg viewBox="0 0 220 220" className="h-40 w-40 sm:h-52 sm:w-52">
              <circle cx="110" cy="110" r="70" fill="none" stroke="#edf2ea" strokeWidth="28" />
              {filtered.map((item, index) => {
                const sweep = ((item[valueKey] as number) / total) * 360;
                const startAngle = currentAngle;
                const endAngle = currentAngle + sweep;
                currentAngle = endAngle;

                return (
                  <path
                    key={`${item.work_code}-${valueKey}-${index}`}
                    d={describeArc(110, 110, 70, startAngle, endAngle)}
                    fill="none"
                    stroke={SLICE_COLORS[index % SLICE_COLORS.length]}
                    strokeWidth="28"
                    strokeLinecap="butt"
                  />
                );
              })}
              <circle cx="110" cy="110" r="46" fill="#ffffff" />
              <text
                x="110"
                y="103"
                textAnchor="middle"
                className="fill-slate-500 text-[10px] font-semibold uppercase tracking-[0.18em]"
              >
                {centerLabel}
              </text>
              <text
                x="110"
                y="124"
                textAnchor="middle"
                className="fill-slate-800 text-[16px] font-bold"
              >
                {centerValue}
              </text>
            </svg>
          </div>

          <div className="mt-2 space-y-1.5">
            {filtered.map((item, index) => {
              const value = item[valueKey] as number;
              const pct = total ? Math.round((value / total) * 100) : 0;
              const displayValue =
                valueKey === "days" ? formatDaysLabel(value) : `${value.toFixed(0)} ${suffix}`;

              return (
                <div
                  key={`${item.work_code}-${item.work_name}-${valueKey}-legend`}
                  className="flex items-start gap-2 text-sm"
                >
                  <span
                    className="mt-1 h-3 w-3 rounded-full"
                    style={{ backgroundColor: SLICE_COLORS[index % SLICE_COLORS.length] }}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium text-slate-700">{formatWorkLabel(item)}</div>
                    <div className="text-xs text-slate-500">
                      {displayValue} · {pct}%
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <div className="mt-3 text-sm text-slate-500">No values found for this chart.</div>
      )}
    </div>
  );
}

export default function EmployeeWorkSummary({
  items,
  records,
  pluckingShare,
  employeeName,
}: Props) {
  if (!items.length) return null;

  const dayChartData = buildChartData(buildDayShareData(records));

  const pluckingItems = items.filter((item) => {
    const label = `${item.work_code} ${item.work_name}`.toLowerCase();
    return (
      label.includes("pluck") ||
      item.work_code.toLowerCase() === "plk" ||
      item.work_code.toLowerCase() === "plucker"
    );
  });

  const totalDays = Array.from(new Set(records.map((record) => record.date))).length;
  const pluckingDays = pluckingItems.reduce((sum, item) => sum + item.days, 0);
  const pluckingKilos = pluckingItems.reduce((sum, item) => sum + item.kilos, 0);

  const shareItems: EmployeeWorkSummaryItem[] = [
    {
      work_code: employeeName,
      work_name: "",
      days: 0,
      kilos: pluckingShare.employee_plucking_kilos,
    },
    {
      work_code: pluckingShare.division ? `${pluckingShare.division} others` : "Division others",
      work_name: "",
      days: 0,
      kilos: pluckingShare.other_division_plucking_kilos,
    },
  ].filter((item) => item.kilos > 0);

  return (
    <section className="panel-soft p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="section-title">Selected Employee Work Summary</div>
          <div className="mt-1 text-sm text-slate-500"></div>
        </div>

        <div className="flex flex-wrap gap-2">
          <div className="pastel-pill">{formatDaysLabel(totalDays)}</div>
          {pluckingDays > 0 ? <div className="pastel-pill">{formatDaysLabel(pluckingDays)}</div> : null}
          {pluckingKilos > 0 ? <div className="pastel-pill">{pluckingKilos.toFixed(0)} kg</div> : null}
        </div>
      </div>

      <div className="mt-3 grid gap-2 xl:grid-cols-2">
        <DonutChart
          title="Work Days Share"
          subtitle=""
          items={dayChartData}
          valueKey="days"
          centerLabel="Total"
          centerValue={formatDaysLabel(totalDays)}
          suffix="days"
        />

        <DonutChart
          title="Plucking Kilo Share"
          items={shareItems}
          valueKey="kilos"
          centerLabel="Plucking"
          centerValue={`${pluckingShare.employee_plucking_kilos.toFixed(0)} kg`}
          suffix="kg"
        />
      </div>
    </section>
  );
}