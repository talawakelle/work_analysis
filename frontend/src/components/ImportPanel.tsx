import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Check,
  FileSpreadsheet,
  Loader2,
  SearchCheck,
  Upload,
  X,
} from "lucide-react";
import { uploadWorkbook, validateWorkbook } from "../api/queries";
import type { ImportValidationResponse } from "../lib/types";

type Props = {
  enabled?: boolean;
};

function ValidationSummary({ validation }: { validation: ImportValidationResponse }) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
        <div className="subtle-card px-3 py-2.5">
          <div className="eyebrow">Detected Period</div>
          <div className="mt-1 font-semibold text-slate-800">{validation.validated_period || "-"}</div>
        </div>
        <div className="subtle-card px-3 py-2.5">
          <div className="eyebrow">Rows</div>
          <div className="mt-1 font-semibold text-slate-800">{(validation.validated_rows ?? 0).toLocaleString()}</div>
        </div>
        <div className="subtle-card px-3 py-2.5">
          <div className="eyebrow">Sheets</div>
          <div className="mt-1 font-semibold text-slate-800">{validation.validated_sheets ?? 0}</div>
        </div>
        <div className="subtle-card px-3 py-2.5">
          <div className="eyebrow">Estates</div>
          <div className="mt-1 font-semibold text-slate-800">{validation.validated_estates.length}</div>
        </div>
      </div>

      {validation.validation_errors.length ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-700">
          <div className="font-semibold">Validation errors</div>
          <ul className="mt-2 space-y-1">
            {validation.validation_errors.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {validation.validation_warnings.length ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-800">
          <div className="font-semibold">Warnings</div>
          <ul className="mt-2 space-y-1">
            {validation.validation_warnings.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="table-shell">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="table-head">
              <tr>
                <th className="px-3 py-2.5">Sheet</th>
                <th className="px-3 py-2.5">Estate</th>
                <th className="px-3 py-2.5">Rows</th>
                <th className="px-3 py-2.5">Missing Columns</th>
                <th className="px-3 py-2.5">Warnings</th>
              </tr>
            </thead>
            <tbody>
              {validation.validation_sheet_results.map((item) => (
                <tr key={item.sheet_name} className="table-row border-t">
                  <td className="px-3 py-2.5 font-medium text-slate-800">{item.sheet_name}</td>
                  <td className="px-3 py-2.5 text-slate-700">{item.estate || "-"}</td>
                  <td className="px-3 py-2.5 text-slate-700">{item.rows.toLocaleString()}</td>
                  <td className="px-3 py-2.5 text-slate-700">{item.missing_columns.join(", ") || "-"}</td>
                  <td className="px-3 py-2.5 text-slate-700">{item.warnings.join(" • ") || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function ImportPanel({ enabled = true }: Props) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [label, setLabel] = useState("");
  const [latestValidation, setLatestValidation] = useState<ImportValidationResponse | null>(null);

  const validateMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Choose a workbook first.");
      return validateWorkbook(file, label);
    },
    onSuccess: (data) => {
      setLatestValidation(data);
      queryClient.invalidateQueries({ queryKey: ["admin-audit"] });
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Choose a workbook first.");
      return uploadWorkbook(file, label);
    },
    onSuccess: (data) => {
      setLatestValidation({
        source_filename: data.source_filename,
        validation_message: data.validation_message,
        validated_period: data.validated_period,
        validated_rows: data.validated_rows,
        validated_sheets: data.validated_sheets,
        validated_estates: data.validated_estates,
        validation_warnings: data.validation_warnings,
        validation_errors: data.validation_errors,
        validation_sheet_results: data.validation_sheet_results,
      });
      setFile(null);
      setLabel("");
      if (inputRef.current) inputRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["imports"] });
      queryClient.invalidateQueries({ queryKey: ["meta"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["analysis"] });
      queryClient.invalidateQueries({ queryKey: ["admin-overview"] });
      queryClient.invalidateQueries({ queryKey: ["admin-audit"] });
    },
  });

  const activeError =
    (validateMutation.error instanceof Error ? validateMutation.error.message : null) ||
    (uploadMutation.error instanceof Error ? uploadMutation.error.message : null);

  if (!enabled) return null;

  return (
    <section className="panel px-3 py-3 sm:px-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-lg font-semibold text-slate-800">
            <FileSpreadsheet className="h-5 w-5 text-[#7aa38b]" />
            <span>Dataset Upload Center</span>
          </div>
          <div className="mt-1 text-sm text-slate-500">
            Validate the workbook first, then upload it. Invalid formats are blocked before any data is written.
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="btn-tab inline-flex items-center gap-2 px-3 py-2"
          >
            <FileSpreadsheet className="h-4 w-4" />
            Choose File
          </button>
          <button
            type="button"
            onClick={() => validateMutation.mutate()}
            disabled={!file || validateMutation.isPending || uploadMutation.isPending}
            className="btn-tab inline-flex items-center gap-2 px-3 py-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {validateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <SearchCheck className="h-4 w-4" />}
            Validate Only
          </button>
          <button
            type="button"
            onClick={() => uploadMutation.mutate()}
            disabled={!file || validateMutation.isPending || uploadMutation.isPending}
            className="btn-primary inline-flex items-center gap-2 px-3 py-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {uploadMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            Validate & Import
          </button>
          {file ? (
            <button
              type="button"
              onClick={() => {
                setFile(null);
                setLabel("");
                setLatestValidation(null);
                if (inputRef.current) inputRef.current.value = "";
              }}
              className="btn-tab inline-flex items-center gap-2 px-3 py-2"
            >
              <X className="h-4 w-4" />
              Clear
            </button>
          ) : null}
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
        <label className="soft-block block p-3">
          <div className="eyebrow">Import Label</div>
          <input
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder="Optional, for example 2026-03"
            className="mt-2 w-full bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
          />
        </label>

        <div className="soft-block p-3">
          <div className="eyebrow">Selected File</div>
          <div className="mt-2 text-sm text-slate-700">
            {file ? file.name : "No workbook selected yet"}
          </div>
          {latestValidation?.validation_message ? (
            <div className="mt-2 flex items-start gap-2 text-xs text-slate-500">
              <Check className="mt-0.5 h-3.5 w-3.5 text-[#7aa38b]" />
              <span>{latestValidation.validation_message}</span>
            </div>
          ) : null}
        </div>
      </div>

      {activeError ? (
        <div className="mt-3 flex items-start gap-2 rounded-2xl border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{activeError}</span>
        </div>
      ) : null}

      {latestValidation ? (
        <div className="mt-3">
          <ValidationSummary validation={latestValidation} />
        </div>
      ) : null}
    </section>
  );
}
