type Props = {
  month: string;
  minDate?: string | null;
  maxDate?: string | null;
  onChange: (value: string) => void;
};

function toMonth(value?: string | null) {
  return value ? value.slice(0, 7) : "";
}

export default function DateRangePicker({ month, minDate, maxDate, onChange }: Props) {
  return (
    <div className="flex min-w-0 items-center rounded-2xl border border-[#d9e4da] bg-white/70 px-1.5 py-1.5">
      <input
        type="month"
        value={month}
        min={toMonth(minDate)}
        max={toMonth(maxDate)}
        onChange={(e) => onChange(e.target.value)}
        className="w-full min-w-0 rounded-xl border border-[#d9e4da] bg-white/80 px-2 py-1.5 text-sm text-slate-700 outline-none"
      />
    </div>
  );
}
