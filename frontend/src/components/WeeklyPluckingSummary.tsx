import { useMemo } from "react";
import type { WeeklyPluckingSummaryItem } from "../lib/types";

type Props = {
  items: WeeklyPluckingSummaryItem[];
};

function formatAvg(value: number) {
  return `${Math.round(value)}`;
}

function formatKg(value: number) {
  return `${value.toFixed(0)} kg`;
}

function ordinalWeek(value: number) {
  if (value === 1) return "1st";
  if (value === 2) return "2nd";
  if (value === 3) return "3rd";
  return `${value}th`;
}

function niceCeil(value: number) {
  if (value <= 0) return 100;
  const rough = value / 4;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const normalized = rough / magnitude;
  let step = 10;
  if (normalized <= 1) step = 1;
  else if (normalized <= 2) step = 2;
  else if (normalized <= 2.5) step = 2.5;
  else if (normalized <= 5) step = 5;
  const niceStep = step * magnitude;
  return niceStep * 4;
}

export default function WeeklyPluckingSummary({ items }: Props) {
  const usableItems = useMemo(
    () => items.filter((item) => item.weekday_total_kilos > 0 || item.weekend_total_kilos > 0),
    [items],
  );

  if (!usableItems.length) return null;

  const rawMax = Math.max(
    ...usableItems.flatMap((item) => [item.weekday_avg_kilos, item.weekend_avg_kilos]),
    1,
  );
  const tickCount = 4;
  const maxValue = niceCeil(rawMax);
  const tickValues = Array.from({ length: tickCount + 1 }, (_, index) =>
    Math.round((maxValue * (tickCount - index)) / tickCount),
  );

  const columnTemplate = `repeat(${usableItems.length}, minmax(120px, 1fr))`;

  return (
    <section className="soft-block p-4 sm:p-5">
      <div className="space-y-5">
        <div>
          <div className="text-sm font-semibold text-slate-700">Weekly Plucking Average</div>
          <div className="text-xs text-slate-500">
            Average kilos per day for Monday-Saturday and Sunday plucking.
          </div>
        </div>

        <div className="grid grid-cols-[36px_1fr] gap-2 sm:grid-cols-[52px_1fr] sm:gap-3">
          <div className="flex h-64 flex-col justify-between pb-10 text-[11px] text-slate-400 sm:h-80">
            {tickValues.map((tick, index) => (
              <div key={`${tick}-${index}`}>{tick}</div>
            ))}
          </div>

          <div className="space-y-4">
            <div className="relative h-64 rounded-3xl border border-[rgba(217,228,218,0.95)] bg-white/70 px-4 pb-10 pt-3 sm:h-80 sm:px-5">
              <div className="pointer-events-none absolute inset-x-4 bottom-10 top-3 flex flex-col justify-between sm:inset-x-5">
                {tickValues.map((tick, index) => (
                  <div
                    key={`${tick}-grid-${index}`}
                    className="border-t border-dashed border-[rgba(191,210,194,0.7)]"
                  />
                ))}
              </div>

              <div
                className="relative z-10 grid h-full items-end gap-3 sm:gap-4"
                style={{ gridTemplateColumns: columnTemplate }}
              >
                {usableItems.map((item) => {
                  const weekdayHeight = `${Math.max(
                    (item.weekday_avg_kilos / maxValue) * 100,
                    item.weekday_avg_kilos > 0 ? 8 : 0,
                  )}%`;
                  const sundayHeight = `${Math.max(
                    (item.weekend_avg_kilos / maxValue) * 100,
                    item.weekend_avg_kilos > 0 ? 8 : 0,
                  )}%`;
                  const label = ordinalWeek(item.week_number);

                  return (
                    <div key={item.week_number} className="flex h-full min-w-0 flex-col justify-end">
                      <div className="flex flex-1 items-end justify-center gap-2">
                        <div className="flex h-full w-1/2 flex-col justify-end gap-1">
                          <div className="text-center text-[10px] font-semibold text-slate-500">
                            {formatAvg(item.weekday_avg_kilos)}
                          </div>
                          <div
                            className="w-full rounded-t-2xl bg-emerald-400/85"
                            style={{ height: weekdayHeight }}
                            title={`${label} Mon-Sat avg ${formatAvg(item.weekday_avg_kilos)}`}
                          />
                        </div>

                        <div className="flex h-full w-1/2 flex-col justify-end gap-1">
                          <div className="text-center text-[10px] font-semibold text-slate-500">
                            {formatAvg(item.weekend_avg_kilos)}
                          </div>
                          <div
                            className="w-full rounded-t-2xl"
                            style={{ height: sundayHeight, backgroundColor: "rgba(245, 200, 64, 0.9)" }}
                            title={`${label} Sunday avg ${formatAvg(item.weekend_avg_kilos)}`}
                          />
                        </div>
                      </div>

                      <div className="mt-2 text-center text-xs font-medium text-slate-600 sm:text-sm">
                        {label}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-wrap gap-5 text-sm">
              <div className="flex items-center gap-2 text-slate-500">
                <span className="h-3.5 w-3.5 rounded-full bg-emerald-400/85" />
                Mon-Sat avg
              </div>
              <div className="flex items-center gap-2 text-slate-500">
                <span className="h-3.5 w-3.5 rounded-full bg-amber-400/90" />
                Sunday avg
              </div>
            </div>

            <div>
              <div className="text-sm font-semibold text-slate-700">Weekly Plucking Totals</div>
            </div>

            <div className="grid gap-3 sm:gap-4" style={{ gridTemplateColumns: columnTemplate }}>
              {usableItems.map((item) => (
                <div
                  key={`weekly-total-${item.week_number}`}
                  className="subtle-card min-w-0 px-3 py-4 sm:px-4"
                >
                  <div className="text-center text-sm font-semibold text-slate-700">
                    {ordinalWeek(item.week_number)}
                  </div>

                  <div className="mt-4 space-y-3">
                    <div className="rounded-3xl bg-[#f6faf5] px-4 py-3">
                      <div className="text-[9px] uppercase tracking-[0.14em] text-slate-400">
                        Mon-Sat total
                      </div>
                      <div className="mt-2 text-base font-semibold leading-tight text-slate-700 sm:text-lg">
                        {formatKg(item.weekday_total_kilos)}
                      </div>
                      <div className="mt-1.5 text-[11px] leading-snug text-slate-500">
                        Avg {formatAvg(item.weekday_avg_kilos)} kg/day
                      </div>
                    </div>

                    <div className="rounded-3xl bg-[#fbf7ea] px-4 py-3">
                      <div className="text-[9px] uppercase tracking-[0.14em] text-slate-400">
                        Sunday total
                      </div>
                      <div className="mt-2 text-base font-semibold leading-tight text-slate-700 sm:text-lg">
                        {formatKg(item.weekend_total_kilos)}
                      </div>
                      <div className="mt-1.5 text-[11px] leading-snug text-slate-500">
                        Avg {formatAvg(item.weekend_avg_kilos)} kg/day
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}