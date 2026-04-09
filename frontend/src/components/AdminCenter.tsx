import { useQuery } from "@tanstack/react-query";
import { Activity, Database, FileClock, ShieldCheck } from "lucide-react";
import { fetchAdminAudit, fetchAdminOverview } from "../api/queries";
import type { AdminAuditEvent } from "../lib/types";
import AccessConfigPanel from "./AccessConfigPanel";
import ImportPanel from "./ImportPanel";
import SummaryCards from "./SummaryCards";

function formatAuditDetails(event: AdminAuditEvent) {
  const details = event.details || {};
  const importantKeys = ["validated_period", "rows_processed", "validated_rows", "users_count", "estates_count", "label"];
  const parts = importantKeys
    .map((key) => {
      const value = details[key];
      if (value === undefined || value === null || value === "") return null;
      return `${key.replace(/_/g, " ")}: ${String(value)}`;
    })
    .filter(Boolean);

  return parts.join(" • ");
}

export default function AdminCenter() {
  const overview = useQuery({
    queryKey: ["admin-overview"],
    queryFn: fetchAdminOverview,
  });

  const audit = useQuery({
    queryKey: ["admin-audit"],
    queryFn: () => fetchAdminAudit(120),
  });

  return (
    <div className="space-y-3">
      <section className="panel px-3 py-3 sm:px-4">
        <div className="flex items-center gap-2 text-lg font-semibold text-slate-800">
          <ShieldCheck className="h-5 w-5 text-[#7aa38b]" />
          <span>Admin Center</span>
        </div>
        <div className="mt-1 text-sm text-slate-500">
          Coverage, data freshness, import validation, access-document updates, and the audit trail are visible only to ADMIN.
        </div>
      </section>

      {overview.data?.freshness_cards?.length ? <SummaryCards items={overview.data.freshness_cards} /> : null}

      <section className="panel px-3 py-3 sm:px-4">
        <div className="flex items-center gap-2 text-lg font-semibold text-slate-800">
          <Database className="h-5 w-5 text-[#7aa38b]" />
          <span>Coverage by Plantation</span>
        </div>
        <div className="mt-3 table-shell">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-3 py-2.5">Plantation</th>
                  <th className="px-3 py-2.5">Configured Estates</th>
                  <th className="px-3 py-2.5">With Data</th>
                  <th className="px-3 py-2.5">Missing Data</th>
                </tr>
              </thead>
              <tbody>
                {(overview.data?.coverage ?? []).map((item) => (
                  <tr key={item.plantation} className="table-row border-t">
                    <td className="px-3 py-2.5 font-medium text-slate-800">{item.plantation}</td>
                    <td className="px-3 py-2.5 text-slate-700">{item.total_estates}</td>
                    <td className="px-3 py-2.5 text-slate-700">{item.estates_with_data}</td>
                    <td className="px-3 py-2.5 text-slate-700">{item.estates_missing_data}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {overview.isLoading ? <div className="px-3 py-3 text-sm text-slate-500">Loading coverage...</div> : null}
        </div>
      </section>

      <ImportPanel enabled />

      <section className="panel px-3 py-3 sm:px-4">
        <div className="flex items-center gap-2 text-lg font-semibold text-slate-800">
          <FileClock className="h-5 w-5 text-[#7aa38b]" />
          <span>Access Document</span>
        </div>
        <div className="mt-1 text-sm text-slate-500">
          Upload the estate username/password document here when it changes. The live access JSON files update automatically.
        </div>
        <div className="mt-3">
          <AccessConfigPanel enabled />
        </div>
      </section>

      <section className="panel px-3 py-3 sm:px-4">
        <div className="flex items-center gap-2 text-lg font-semibold text-slate-800">
          <Activity className="h-5 w-5 text-[#7aa38b]" />
          <span>Recent Import History</span>
        </div>
        <div className="mt-3 table-shell">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-3 py-2.5">When</th>
                  <th className="px-3 py-2.5">Label</th>
                  <th className="px-3 py-2.5">File</th>
                  <th className="px-3 py-2.5">Rows</th>
                  <th className="px-3 py-2.5">Range</th>
                </tr>
              </thead>
              <tbody>
                {(overview.data?.recent_imports ?? []).map((item) => (
                  <tr key={item.id} className="table-row border-t">
                    <td className="px-3 py-2.5 text-slate-700">{new Date(item.created_at).toLocaleString()}</td>
                    <td className="px-3 py-2.5 font-medium text-slate-800">{item.label}</td>
                    <td className="px-3 py-2.5 text-slate-700">{item.source_filename}</td>
                    <td className="px-3 py-2.5 text-slate-700">{item.rows_processed.toLocaleString()}</td>
                    <td className="px-3 py-2.5 text-slate-700">
                      {item.month_start && item.month_end ? `${item.month_start} → ${item.month_end}` : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {overview.isLoading ? <div className="px-3 py-3 text-sm text-slate-500">Loading imports...</div> : null}
        </div>
      </section>

      <section className="panel px-3 py-3 sm:px-4">
        <div className="flex items-center gap-2 text-lg font-semibold text-slate-800">
          <ShieldCheck className="h-5 w-5 text-[#7aa38b]" />
          <span>Audit Trail</span>
        </div>
        <div className="mt-1 text-sm text-slate-500">
          Shows recent logins, validations, uploads, and access-document changes.
        </div>
        <div className="mt-3 table-shell">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-3 py-2.5">Time</th>
                  <th className="px-3 py-2.5">Event</th>
                  <th className="px-3 py-2.5">User</th>
                  <th className="px-3 py-2.5">Target</th>
                  <th className="px-3 py-2.5">Details</th>
                </tr>
              </thead>
              <tbody>
                {(audit.data ?? []).map((item) => (
                  <tr key={item.id} className="table-row border-t align-top">
                    <td className="px-3 py-2.5 text-slate-700">{new Date(item.created_at).toLocaleString()}</td>
                    <td className="px-3 py-2.5 font-medium text-slate-800">{item.event_type}</td>
                    <td className="px-3 py-2.5 text-slate-700">
                      {item.actor_username || "-"}
                      {item.actor_role ? <div className="text-xs text-slate-500">{item.actor_role}</div> : null}
                    </td>
                    <td className="px-3 py-2.5 text-slate-700">
                      {item.target_type || "-"}
                      {item.target_value ? <div className="text-xs text-slate-500">{item.target_value}</div> : null}
                    </td>
                    <td className="px-3 py-2.5 text-slate-700">{formatAuditDetails(item) || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {audit.isLoading ? <div className="px-3 py-3 text-sm text-slate-500">Loading audit trail...</div> : null}
        </div>
      </section>
    </div>
  );
}
