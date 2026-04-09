import { api } from "./client";
import type {
  AccessConfigUploadResponse,
  AdminAuditEvent,
  AdminOverviewResponse,
  AuthLoginResponse,
  DashboardResponse,
  EmployeeDetailResponse,
  EmployeeSearchItem,
  ImportBatchResponse,
  ImportValidationResponse,
  MetaFiltersResponse,
  WorkAnalysisResponse,
} from "../lib/types";

export const fetchMeta = async (params?: Record<string, string | undefined>) => {
  const { data } = await api.get<MetaFiltersResponse>("/meta/filters", { params });
  return data;
};

export const fetchDashboard = async (params: Record<string, string | undefined>) => {
  const { data } = await api.get<DashboardResponse>("/analytics/dashboard", { params });
  return data;
};

export const fetchWorkAnalysis = async (
  params: Record<string, string | number | undefined>,
) => {
  const { data } = await api.get<WorkAnalysisResponse>("/analytics/work-analysis", {
    params,
  });
  return data;
};

export const searchEmployees = async (
  q: string,
  estate?: string,
  plantation?: string,
) => {
  const { data } = await api.get<EmployeeSearchItem[]>("/analytics/employees/search", {
    params: { q, estate, plantation },
  });
  return data;
};

export const fetchEmployeeDetail = async (
  employeeId: number,
  params: Record<string, string | undefined>,
) => {
  const { data } = await api.get<EmployeeDetailResponse>(
    `/analytics/employees/${employeeId}/detail`,
    { params },
  );
  return data;
};

export const fetchImports = async () => {
  const { data } = await api.get<{ items: ImportBatchResponse[] }>("/imports");
  return data.items;
};

function extractApiError(error: unknown, fallback: string) {
  const detail =
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    typeof (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail === "string"
      ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
      : null;
  return detail || fallback;
}

export const validateWorkbook = async (file: File, label?: string) => {
  const formData = new FormData();
  if (label?.trim()) formData.append("label", label.trim());
  formData.append("file", file);

  try {
    const { data } = await api.post<ImportValidationResponse>("/imports/validate", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  } catch (error) {
    throw new Error(extractApiError(error, "Validation failed."));
  }
};

export const uploadWorkbook = async (file: File, label?: string) => {
  const formData = new FormData();
  if (label?.trim()) formData.append("label", label.trim());
  formData.append("file", file);

  try {
    const { data } = await api.post<ImportBatchResponse>("/imports/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  } catch (error) {
    throw new Error(extractApiError(error, "Upload failed."));
  }
};

export const uploadAccessConfig = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const { data } = await api.post<AccessConfigUploadResponse>("/auth/access-config/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  } catch (error) {
    throw new Error(extractApiError(error, "Access document upload failed."));
  }
};

export const fetchAdminOverview = async () => {
  const { data } = await api.get<AdminOverviewResponse>("/admin/overview");
  return data;
};

export const fetchAdminAudit = async (limit = 100) => {
  const { data } = await api.get<{ items: AdminAuditEvent[] }>("/admin/audit", { params: { limit } });
  return data.items;
};

export const loginWithCredentials = async (username: string, password: string) => {
  const { data } = await api.post<AuthLoginResponse>("/auth/login", { username, password });
  return data;
};
