export type SummaryCard = {
  label: string;
  value: string | number;
};

export type WorkCodeSummaryItem = {
  work_code: string;
  work_name: string;
  days: number;
  records: number;
};

export type AuthLoginResponse = {
  username: string;
  display_name: string | null;
  resolved_estate: string | null;
  accessible_estates: string[];
  accessible_plantations: string[];
  selected_plantation: string | null;
  role: string;
  can_upload: boolean;
  can_switch_estate: boolean;
  access_mode: "open" | "locked" | "scoped" | "restricted";
  access_message: string | null;
};

export type MetaFiltersResponse = {
  estates: string[];
  min_date: string | null;
  max_date: string | null;
  import_labels: string[];
  resolved_user: string | null;
  display_name: string | null;
  resolved_estate: string | null;
  accessible_estates: string[];
  accessible_plantations: string[];
  selected_plantation: string | null;
  role: string;
  can_switch_estate: boolean;
  can_upload: boolean;
  access_mode: "open" | "locked" | "scoped" | "restricted";
  access_message: string | null;
};

export type DashboardResponse = {
  summary: SummaryCard[];
  work_code_summary: WorkCodeSummaryItem[];
};

export type WorkAnalysisRow = {
  employee_id: number;
  employee_no: string;
  employee_name: string;
  estate: string;
  division: string | null;
  employment_type: string | null;
  total_kilos: number;
  total_days: number;
  avg_kilos_per_day: number;
  row_color: "light-green" | "red" | "amber" | "neutral";
};

export type WeeklyPluckingSummaryItem = {
  week_label: string;
  week_number: number;
  weekday_total_kilos: number;
  weekend_total_kilos: number;
  weekday_days: number;
  weekend_days: number;
  weekday_avg_kilos: number;
  weekend_avg_kilos: number;
};

export type WorkAnalysisResponse = {
  summary: SummaryCard[];
  work_code_summary: WorkCodeSummaryItem[];
  weekly_plucking: WeeklyPluckingSummaryItem[];
  rows: WorkAnalysisRow[];
};

export type EmployeeSearchItem = {
  employee_id: number;
  employee_no: string;
  employee_name: string;
  estate: string;
  division: string | null;
};

export type CalendarDay = {
  date: string;
  kilos: number;
  worked: boolean;
  work_hour: number | null;
  work_code: string | null;
  work_name: string | null;
  employment_type: string | null;
  division: string | null;
  field_code: string | null;
  gang: string | null;
  plantation: string | null;
  crop: string | null;
  hectare: number | null;
  gender: string | null;
  color: "green" | "red" | "neutral";
};

export type DayDetail = CalendarDay;

export type DailyRecord = {
  date: string;
  division: string | null;
  plantation: string | null;
  crop: string | null;
  field_code: string | null;
  gang: string | null;
  kilos: number;
  work_hour: number | null;
  hectare: number | null;
  work_code: string | null;
  work_name: string | null;
  employment_type: string | null;
  gender: string | null;
};

export type EmployeeProfile = {
  employee_id: number;
  employee_no: string;
  employee_name: string;
  estate: string;
  gender: string | null;
  primary_division: string | null;
  primary_gang: string | null;
};

export type EmployeeWorkSummaryItem = {
  work_code: string;
  work_name: string;
  days: number;
  kilos: number;
};

export type AttendanceSummary = {
  present_days: number;
  absent_days: number;
  total_days: number;
};

export type PluckingKiloShare = {
  division: string | null;
  division_plucking_kilos: number;
  employee_plucking_kilos: number;
  other_division_plucking_kilos: number;
};

export type EmployeeDetailResponse = {
  employee: EmployeeProfile;
  period: string;
  summary: SummaryCard[];
  work_code_summary: WorkCodeSummaryItem[];
  work_summary: EmployeeWorkSummaryItem[];
  attendance: AttendanceSummary;
  plucking_kilo_share: PluckingKiloShare;
  calendar: CalendarDay[];
  records: DailyRecord[];
};

export type ImportValidationSheetResult = {
  sheet_name: string;
  estate: string | null;
  rows: number;
  missing_columns: string[];
  warnings: string[];
};

export type ImportValidationResponse = {
  source_filename: string;
  validation_message: string | null;
  validated_period: string | null;
  validated_rows: number | null;
  validated_sheets: number | null;
  validated_estates: string[];
  validation_warnings: string[];
  validation_errors: string[];
  validation_sheet_results: ImportValidationSheetResult[];
};

export type ImportBatchResponse = {
  id: number;
  label: string;
  source_filename: string;
  month_start: string | null;
  month_end: string | null;
  rows_processed: number;
  status: string;
  created_at: string;
  validation_message: string | null;
  validated_period: string | null;
  validated_rows: number | null;
  validated_sheets: number | null;
  validated_estates: string[];
  validation_warnings: string[];
  validation_errors: string[];
  validation_sheet_results: ImportValidationSheetResult[];
};

export type AccessConfigUploadResponse = {
  source_filename: string;
  estates_count: number;
  estate_user_count: number;
  plantation_codes: string[];
  users_count: number;
  message: string;
  warnings: string[];
};

export type AdminCoverageItem = {
  plantation: string;
  total_estates: number;
  estates_with_data: number;
  estates_missing_data: number;
};

export type AdminImportHistoryItem = {
  id: number;
  label: string;
  source_filename: string;
  created_at: string;
  rows_processed: number;
  status: string;
  month_start: string | null;
  month_end: string | null;
};

export type AdminOverviewResponse = {
  freshness_cards: SummaryCard[];
  coverage: AdminCoverageItem[];
  recent_imports: AdminImportHistoryItem[];
};

export type AdminAuditEvent = {
  id: number;
  event_type: string;
  actor_username: string | null;
  actor_display_name: string | null;
  actor_role: string | null;
  target_type: string | null;
  target_value: string | null;
  details: Record<string, unknown>;
  created_at: string;
};
