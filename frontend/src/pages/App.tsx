import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Lock,
  LogOut,
  Search,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  UserRound,
} from "lucide-react";
import {
  fetchDashboard,
  fetchEmployeeDetail,
  fetchMeta,
  fetchWorkAnalysis,
  loginWithCredentials,
  searchEmployees,
} from "../api/queries";
import AdminCenter from "../components/AdminCenter";
import CalendarGrid from "../components/CalendarGrid";
import DateRangePicker from "../components/DateRangePicker";
import EmployeeAttendanceBox from "../components/EmployeeAttendanceBox";
import EmployeeProfileCard from "../components/EmployeeProfileCard";
import EmployeeRecordsTable from "../components/EmployeeRecordsTable";
import EmployeeWorkSummary from "../components/EmployeeWorkSummary";
import LoginPanel from "../components/LoginPanel";
import SummaryCards from "../components/SummaryCards";
import WeeklyPluckingSummary from "../components/WeeklyPluckingSummary";
import WorkAnalysisTable from "../components/WorkAnalysisTable";
import {
  clearStoredAuthSession,
  getAuthIdentity,
  getStoredAuthSession,
  setStoredAuthSession,
} from "../lib/auth";
import type { CalendarDay, EmployeeSearchItem } from "../lib/types";

type ViewMode = "analysis" | "weekly" | "employee" | "admin";
type Direction = "top" | "bottom";
type Metric = "workers" | "kilos" | "days";

const metricCopy: Record<Metric, string> = {
  workers: "Workers",
  kilos: "Kilos",
  days: "Days",
};

function monthBounds(month: string) {
  const [year, monthIndex] = month.split("-").map(Number);
  const lastDay = new Date(year, monthIndex, 0).getDate();

  return {
    start: `${month}-01`,
    end: `${month}-${String(lastDay).padStart(2, "0")}`,
  };
}

function shiftMonth(ym: string, offset: number) {
  const [year, month] = ym.split("-").map(Number);
  const next = new Date(year, month - 1 + offset, 1);
  return `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}`;
}

function plantationAllLabel(selectedPlantation: string, accessiblePlantations: string[]) {
  const plantation = selectedPlantation || (accessiblePlantations.length === 1 ? accessiblePlantations[0] : "");
  return plantation ? `All ${plantation} estates` : "All accessible estates";
}

export default function App() {
  const queryClient = useQueryClient();
  const initialIdentity = useMemo(() => getAuthIdentity(), []);
  const initialSession = useMemo(() => getStoredAuthSession(), []);
  const [authUsername, setAuthUsername] = useState<string | null>(initialSession?.username || initialIdentity.username);
  const [authDisplayName, setAuthDisplayName] = useState<string | null>(initialSession?.display_name || null);
  const [viewMode, setViewMode] = useState<ViewMode>("analysis");
  const [selectedMonth, setSelectedMonth] = useState("");
  const [selectedPlantation, setSelectedPlantation] = useState("");
  const [selectedEstate, setSelectedEstate] = useState("");
  const [direction, setDirection] = useState<Direction>("top");
  const [metric, setMetric] = useState<Metric>("workers");
  const [value, setValue] = useState("10");
  const [employeeQuery, setEmployeeQuery] = useState("");
  const [selectedEmployee, setSelectedEmployee] = useState<EmployeeSearchItem | null>(null);
  const [selectedDay, setSelectedDay] = useState<CalendarDay | null>(null);
  const [loginError, setLoginError] = useState<string | null>(null);

  const isAuthenticated = Boolean(authUsername);

  const loginMutation = useMutation({
    mutationFn: async (payload: { username: string; password: string }) =>
      loginWithCredentials(payload.username, payload.password),
    onSuccess: (data) => {
      setStoredAuthSession({
        username: data.username,
        display_name: data.display_name,
        resolved_estate: data.resolved_estate,
        role: data.role,
      });
      setAuthUsername(data.username);
      setAuthDisplayName(data.display_name);
      setSelectedPlantation(data.selected_plantation || "");
      setSelectedEstate(data.resolved_estate || "");
      setViewMode(data.role === "admin" ? "admin" : "analysis");
      setSelectedEmployee(null);
      setSelectedDay(null);
      setEmployeeQuery("");
      setLoginError(null);
      queryClient.invalidateQueries();
    },
  });

  async function handleLogin(username: string, password: string) {
    if (!username || !password) {
      setLoginError("Enter both username and password.");
      return;
    }

    try {
      await loginMutation.mutateAsync({ username, password });
    } catch (error) {
      const detail =
        typeof error === "object" &&
        error !== null &&
        "response" in error &&
        typeof (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail === "string"
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setLoginError(detail || "Could not sign in with that username and password.");
    }
  }

  function handleLogout() {
    clearStoredAuthSession();
    setAuthUsername(null);
    setAuthDisplayName(null);
    setSelectedMonth("");
    setSelectedPlantation("");
    setSelectedEstate("");
    setSelectedEmployee(null);
    setSelectedDay(null);
    setEmployeeQuery("");
    setLoginError(null);
    setViewMode("analysis");
    queryClient.clear();
  }

  const metaParams = useMemo(
    () => ({
      plantation: selectedPlantation || undefined,
      estate: selectedEstate || undefined,
    }),
    [selectedPlantation, selectedEstate],
  );

  const { data: meta, isLoading: metaLoading, error: metaError } = useQuery({
    queryKey: ["meta", authUsername, selectedPlantation, selectedEstate],
    queryFn: () => fetchMeta(metaParams),
    enabled: isAuthenticated,
  });

  useEffect(() => {
    if (!selectedMonth && meta?.max_date) {
      setSelectedMonth(meta.max_date.slice(0, 7));
    }
  }, [meta, selectedMonth]);

  useEffect(() => {
    if (!meta) return;

    if (meta.display_name) {
      setAuthDisplayName(meta.display_name);
    }

    if (meta.resolved_user) {
      setStoredAuthSession({
        username: meta.resolved_user,
        display_name: meta.display_name,
        resolved_estate: meta.resolved_estate,
        role: meta.role,
      });
      if (meta.resolved_user !== authUsername) {
        setAuthUsername(meta.resolved_user);
      }
    }

    if (!selectedPlantation && meta.accessible_plantations.length === 1) {
      setSelectedPlantation(meta.accessible_plantations[0]);
    }

    if (meta.resolved_estate) {
      if (selectedEstate !== meta.resolved_estate) {
        setSelectedEstate(meta.resolved_estate);
      }
      return;
    }

    if (selectedEstate && !meta.accessible_estates.includes(selectedEstate)) {
      setSelectedEstate("");
      return;
    }

    if (!selectedEstate && meta.accessible_estates.length === 1) {
      setSelectedEstate(meta.accessible_estates[0]);
    }
  }, [meta, authUsername, selectedEstate, selectedPlantation]);

  const filtersReady = Boolean(selectedMonth && isAuthenticated && meta?.access_mode !== "restricted");
  const numberValue = Math.max(Number(value || 0), 1);

  const { start: startDate, end: endDate } = useMemo(
    () => (selectedMonth ? monthBounds(selectedMonth) : { start: "", end: "" }),
    [selectedMonth],
  );

  const dashboard = useQuery({
    queryKey: ["dashboard", authUsername, selectedPlantation, selectedEstate, startDate, endDate],
    queryFn: () =>
      fetchDashboard({
        plantation: selectedPlantation || undefined,
        estate: selectedEstate || undefined,
        start_date: startDate,
        end_date: endDate,
      }),
    enabled: filtersReady && viewMode !== "admin",
  });

  const analysis = useQuery({
    queryKey: ["analysis", authUsername, selectedPlantation, selectedEstate, startDate, endDate, direction, metric, numberValue],
    queryFn: () =>
      fetchWorkAnalysis({
        plantation: selectedPlantation || undefined,
        estate: selectedEstate || undefined,
        start_date: startDate,
        end_date: endDate,
        direction,
        metric,
        value: numberValue,
      }),
    enabled: filtersReady && viewMode !== "admin",
  });

  const employeeSuggestions = useQuery({
    queryKey: ["employee-search", authUsername, selectedPlantation, employeeQuery, selectedEstate],
    queryFn: () => searchEmployees(employeeQuery, selectedEstate || undefined, selectedPlantation || undefined),
    enabled: Boolean(filtersReady && employeeQuery.trim().length >= 1),
  });

  const employeeDetail = useQuery({
    queryKey: ["employee-detail", authUsername, selectedPlantation, selectedEstate, selectedEmployee?.employee_id, selectedMonth],
    queryFn: () =>
      fetchEmployeeDetail(selectedEmployee!.employee_id, {
        ym: selectedMonth,
        plantation: selectedPlantation || undefined,
        estate: selectedEstate || undefined,
      }),
    enabled: Boolean(filtersReady && selectedEmployee),
  });

  useEffect(() => {
    const preferredDay =
      employeeDetail.data?.calendar.find((item) => item.kilos > 0 || item.work_code) ??
      employeeDetail.data?.calendar[0] ??
      null;
    setSelectedDay(preferredDay);
  }, [employeeDetail.data]);

  const selectedDayRows = useMemo(
    () => (selectedDay ? (employeeDetail.data?.records ?? []).filter((row) => row.date === selectedDay.date) : []),
    [employeeDetail.data, selectedDay],
  );

  const accessTitle = meta?.display_name || authDisplayName || meta?.resolved_user || authUsername || "Guest";
  const plantationScopeLabel =
    selectedPlantation || (meta?.accessible_plantations?.length === 1 ? meta.accessible_plantations[0] : "ALL");
  const showPlantationButtons = Boolean(meta?.accessible_plantations && meta.accessible_plantations.length > 1);

  const minMonth = meta?.min_date?.slice(0, 7) || "";
  const maxMonth = meta?.max_date?.slice(0, 7) || "";
  const previousMonthDisabled = !selectedMonth || Boolean(minMonth && selectedMonth <= minMonth);
  const nextMonthDisabled = !selectedMonth || Boolean(maxMonth && selectedMonth >= maxMonth);

  if (!isAuthenticated) {
    return (
      <div className="app-shell">
        <LoginPanel onSubmit={handleLogin} loading={loginMutation.isPending} error={loginError} />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-3 px-3 py-3 sm:px-4 lg:px-6">
        <header className="panel px-3 py-3 sm:px-4">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <div className="inline-flex items-center gap-2 rounded-2xl bg-slate-50 px-3 py-2 text-sm text-slate-700">
                  <ShieldCheck className="h-4 w-4 text-[#7aa38b]" />
                  <span className="truncate">{accessTitle}</span>
                </div>

                <div className="inline-flex items-center gap-2 rounded-2xl bg-slate-50 px-3 py-2 text-sm text-slate-700">
                  <Building2 className="h-4 w-4 text-[#7aa38b]" />
                  <span className="truncate">Plantation {plantationScopeLabel}</span>
                </div>

                <div className="inline-flex items-center gap-2 rounded-2xl bg-slate-50 px-3 py-2 text-sm text-slate-700">
                  <Building2 className="h-4 w-4 text-[#7aa38b]" />
                  <span className="truncate">
                    {selectedEstate || plantationAllLabel(selectedPlantation, meta?.accessible_plantations ?? [])}
                  </span>
                </div>

                {!meta?.can_switch_estate && selectedEstate ? (
                  <div className="inline-flex items-center gap-2 rounded-2xl bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                    <Lock className="h-4 w-4" />
                    <span>Locked by login</span>
                  </div>
                ) : null}
              </div>

              {meta?.access_message ? (
                <div className="mt-2 text-sm text-slate-500">{meta.access_message}</div>
              ) : null}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {meta?.can_switch_estate ? (
                <label className="soft-block min-w-[220px] px-3 py-2">
                  <div className="eyebrow">Estate</div>
                  <select
                    value={selectedEstate}
                    onChange={(event) => {
                      setSelectedEstate(event.target.value);
                      setSelectedEmployee(null);
                      setSelectedDay(null);
                    }}
                    className="mt-1 w-full bg-transparent text-sm text-slate-800 outline-none"
                  >
                    <option value="">{plantationAllLabel(selectedPlantation, meta?.accessible_plantations ?? [])}</option>
                    {meta?.accessible_estates.map((estate) => (
                      <option key={estate} value={estate}>
                        {estate}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}

              <DateRangePicker
                month={selectedMonth}
                minDate={meta?.min_date}
                maxDate={meta?.max_date}
                onChange={(nextMonth) => {
                  setSelectedMonth(nextMonth);
                  setSelectedDay(null);
                }}
              />

              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center gap-2 rounded-2xl border border-[#d4ddd2] bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
              >
                <LogOut className="h-4 w-4" />
                Log out
              </button>
            </div>
          </div>

          {showPlantationButtons ? (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                onClick={() => {
                  setSelectedPlantation("");
                  setSelectedEstate("");
                  setSelectedEmployee(null);
                  setSelectedDay(null);
                }}
                className={`inline-flex min-w-0 items-center justify-center gap-1.5 rounded-2xl px-3 py-2 text-sm font-semibold transition ${
                  !selectedPlantation ? "btn-tab-active" : "btn-tab"
                }`}
              >
                ALL
              </button>
              {meta?.accessible_plantations.map((plantation) => (
                <button
                  key={plantation}
                  onClick={() => {
                    setSelectedPlantation(plantation);
                    setSelectedEstate("");
                    setSelectedEmployee(null);
                    setSelectedDay(null);
                  }}
                  className={`inline-flex min-w-0 items-center justify-center gap-1.5 rounded-2xl px-3 py-2 text-sm font-semibold transition ${
                    selectedPlantation === plantation ? "btn-tab-active" : "btn-tab"
                  }`}
                >
                  {plantation}
                </button>
              ))}
            </div>
          ) : null}

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              onClick={() => setViewMode("analysis")}
              className={`inline-flex min-w-0 items-center justify-center gap-1.5 rounded-2xl px-3 py-2 text-sm font-semibold transition ${
                viewMode === "analysis" ? "btn-tab-active" : "btn-tab"
              }`}
            >
              <TrendingUp className="h-4 w-4" />
              Work Analysis
            </button>

            <button
              onClick={() => setViewMode("weekly")}
              className={`inline-flex min-w-0 items-center justify-center gap-1.5 rounded-2xl px-3 py-2 text-sm font-semibold transition ${
                viewMode === "weekly" ? "btn-tab-active" : "btn-tab"
              }`}
            >
              <TrendingDown className="h-4 w-4" />
              Weekly Progress
            </button>

            <button
              onClick={() => setViewMode("employee")}
              className={`inline-flex min-w-0 items-center justify-center gap-1.5 rounded-2xl px-3 py-2 text-sm font-semibold transition ${
                viewMode === "employee" ? "btn-tab-active" : "btn-tab"
              }`}
            >
              <UserRound className="h-4 w-4" />
              Employee Details
            </button>

            {meta?.role === "admin" ? (
              <button
                onClick={() => setViewMode("admin")}
                className={`inline-flex min-w-0 items-center justify-center gap-1.5 rounded-2xl px-3 py-2 text-sm font-semibold transition ${
                  viewMode === "admin" ? "btn-tab-active" : "btn-tab"
                }`}
              >
                <ShieldCheck className="h-4 w-4" />
                Admin Center
              </button>
            ) : null}
          </div>
        </header>

        {metaLoading ? (
          <section className="panel px-4 py-3 text-sm text-slate-600">Loading estate access and dataset...</section>
        ) : null}

        {metaError ? (
          <section className="panel px-4 py-3 text-sm text-red-600">
            Could not load access metadata.
          </section>
        ) : null}

        {!metaLoading && meta?.access_mode === "restricted" ? (
          <section className="panel px-4 py-4 text-sm text-red-700">
            {meta.access_message || "This account does not have estate access."}
          </section>
        ) : (
          <>
            {viewMode !== "admin" ? <SummaryCards items={dashboard.data?.summary ?? []} /> : null}

            {viewMode === "admin" ? (
              <AdminCenter />
            ) : (
              <section className="panel px-3 py-3 sm:px-4 sm:py-4">
                <div className="flex items-center gap-3 text-lg font-semibold text-slate-800">
                  {viewMode === "analysis" ? (
                    <TrendingDown className="h-5 w-5 text-[#7aa38b]" />
                  ) : viewMode === "weekly" ? (
                    <TrendingUp className="h-5 w-5 text-[#7aa38b]" />
                  ) : (
                    <CalendarDays className="h-5 w-5 text-[#7aa38b]" />
                  )}
                  <span>
                    {viewMode === "analysis"
                      ? "Work Analysis"
                      : viewMode === "weekly"
                        ? "Weekly Progress"
                        : "Employee Details"}
                  </span>
                </div>

                {viewMode === "analysis" ? (
                  <div className="mt-3 space-y-3">
                    <div className="grid grid-cols-1 gap-2 xl:grid-cols-[1fr_1.25fr_180px]">
                      <div className="soft-block min-w-0 p-2.5">
                        <div className="eyebrow">Direction</div>
                        <div className="mt-1.5 grid grid-cols-2 gap-2">
                          {(["top", "bottom"] as Direction[]).map((item) => (
                            <button
                              key={item}
                              onClick={() => setDirection(item)}
                              className={`rounded-2xl px-3 py-2 text-sm font-semibold ${
                                direction === item ? "btn-tab-active" : "btn-tab"
                              }`}
                            >
                              {item === "top" ? "Top" : "Bottom"}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="soft-block min-w-0 p-2.5">
                        <div className="eyebrow">Metric</div>
                        <div className="mt-1.5 grid grid-cols-3 gap-2">
                          {(["workers", "kilos", "days"] as Metric[]).map((item) => (
                            <button
                              key={item}
                              onClick={() => setMetric(item)}
                              className={`rounded-2xl px-3 py-2 text-sm font-semibold ${
                                metric === item ? "btn-tab-active" : "btn-tab"
                              }`}
                            >
                              {metricCopy[item]}
                            </button>
                          ))}
                        </div>
                      </div>

                      <label className="soft-block min-w-0 p-2.5">
                        <div className="eyebrow">Value</div>
                        <input
                          type="number"
                          min={1}
                          value={value}
                          onChange={(e) => setValue(e.target.value)}
                          className="mt-1 w-full bg-transparent py-2 text-2xl font-semibold text-slate-800 outline-none"
                        />
                      </label>
                    </div>

                    {analysis.isLoading ? (
                      <div className="table-shell px-5 py-6 text-sm text-slate-500">Loading work analysis...</div>
                    ) : analysis.isError ? (
                      <div className="table-shell px-5 py-6 text-sm text-red-600">Could not load work analysis.</div>
                    ) : (
                      <WorkAnalysisTable
                        rows={analysis.data?.rows ?? []}
                        showEstate={Boolean(meta?.can_switch_estate && !selectedEstate)}
                        onSelectEmployee={(row) => {
                          setViewMode("employee");
                          setSelectedEmployee({
                            employee_id: row.employee_id,
                            employee_no: row.employee_no,
                            employee_name: row.employee_name,
                            estate: row.estate,
                            division: row.division,
                          });
                          setEmployeeQuery(`${row.employee_no} - ${row.employee_name}`);
                        }}
                      />
                    )}
                  </div>
                ) : viewMode === "weekly" ? (
                  <div className="mt-3">
                    {analysis.isLoading ? (
                      <div className="table-shell px-5 py-6 text-sm text-slate-500">Loading weekly summary...</div>
                    ) : analysis.isError ? (
                      <div className="table-shell px-5 py-6 text-sm text-red-600">Could not load weekly summary.</div>
                    ) : analysis.data?.weekly_plucking?.length ? (
                      <WeeklyPluckingSummary items={analysis.data.weekly_plucking} />
                    ) : (
                      <div className="table-shell px-5 py-6 text-sm text-slate-500">No weekly plucking records for this filter.</div>
                    )}
                  </div>
                ) : (
                  <div className="mt-3 space-y-3">
                    <div className="soft-block p-2">
                      <div className="flex items-center gap-2">
                        <Search className="h-4 w-4 text-slate-500" />
                        <input
                          value={employeeQuery}
                          onChange={(e) => {
                            setEmployeeQuery(e.target.value);
                            if (!e.target.value.trim()) setSelectedEmployee(null);
                          }}
                          placeholder={selectedEstate ? `Search employee in ${selectedEstate}` : "Search employee"}
                          className="w-full bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-400"
                        />
                      </div>

                      {employeeSuggestions.isLoading ? (
                        <div className="mt-2 text-sm text-slate-500">Searching employees...</div>
                      ) : employeeSuggestions.data?.length ? (
                        <div className="mt-2 grid gap-2">
                          {employeeSuggestions.data.map((item) => (
                            <button
                              key={item.employee_id}
                              onClick={() => {
                                setSelectedEmployee(item);
                                setEmployeeQuery(`${item.employee_no} - ${item.employee_name}`);
                              }}
                              className="subtle-card px-3 py-2.5 text-left transition hover:bg-white/90"
                            >
                              <div className="font-medium text-slate-800">
                                {item.employee_no} — {item.employee_name}
                              </div>
                              <div className="mt-1 text-xs text-slate-500">
                                {item.estate}{item.division ? ` • ${item.division}` : ""}
                              </div>
                            </button>
                          ))}
                        </div>
                      ) : employeeQuery.trim() ? (
                        <div className="mt-2 text-sm text-slate-500">No employee matches this search.</div>
                      ) : null}
                    </div>

                    {selectedEmployee ? (
                      <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-slate-50 px-3 py-2">
                        <div className="text-sm text-slate-600">
                          Selected month <span className="font-semibold text-slate-800">{selectedMonth || "-"}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            disabled={previousMonthDisabled}
                            onClick={() => {
                              if (!selectedMonth) return;
                              setSelectedMonth(shiftMonth(selectedMonth, -1));
                              setSelectedDay(null);
                            }}
                            className="btn-tab inline-flex items-center gap-1.5 px-3 py-2 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <ChevronLeft className="h-4 w-4" />
                            Previous month
                          </button>
                          <button
                            type="button"
                            disabled={nextMonthDisabled}
                            onClick={() => {
                              if (!selectedMonth) return;
                              setSelectedMonth(shiftMonth(selectedMonth, 1));
                              setSelectedDay(null);
                            }}
                            className="btn-tab inline-flex items-center gap-1.5 px-3 py-2 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Next month
                            <ChevronRight className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    ) : null}

                    {employeeDetail.isLoading ? (
                      <div className="table-shell px-5 py-6 text-sm text-slate-500">Loading employee detail...</div>
                    ) : employeeDetail.data?.employee ? (
                      <>
                        <EmployeeProfileCard employee={employeeDetail.data.employee} />

                        <div className="space-y-3">
                          <EmployeeWorkSummary
                            items={employeeDetail.data.work_summary ?? []}
                            records={employeeDetail.data.records ?? []}
                            pluckingShare={employeeDetail.data.plucking_kilo_share}
                            employeeName={employeeDetail.data.employee.employee_name}
                          />

                          <CalendarGrid
                            month={selectedMonth}
                            days={employeeDetail.data.calendar ?? []}
                            selectedDate={selectedDay?.date}
                            onSelect={(day) => {
                              setSelectedDay(day);
                            }}
                          />

                          <EmployeeAttendanceBox attendance={employeeDetail.data.attendance} />

                          <EmployeeRecordsTable day={selectedDay} rows={selectedDayRows} />
                        </div>
                      </>
                    ) : (
                      <div className="table-shell px-5 py-6 text-sm text-slate-500">
                        Search and select an employee to view their estate-specific records.
                      </div>
                    )}
                  </div>
                )}
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}
