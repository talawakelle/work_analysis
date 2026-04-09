import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, FileText, Loader2, RefreshCw, Upload } from "lucide-react";
import { uploadAccessConfig } from "../api/queries";

type Props = {
  enabled?: boolean;
};

export default function AccessConfigPanel({ enabled = true }: Props) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      if (!file) {
        inputRef.current?.click();
        throw new Error("Choose an access document");
      }
      return uploadAccessConfig(file);
    },
    onSuccess: () => {
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["meta"] });
      queryClient.invalidateQueries({ queryKey: ["admin-audit"] });
      queryClient.invalidateQueries({ queryKey: ["admin-overview"] });
    },
  });

  if (!enabled) return null;

  return (
    <div className="flex min-w-0 items-center justify-end gap-1.5">
      <input
        ref={inputRef}
        type="file"
        accept=".docx,.csv,.json"
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        className="hidden"
      />

      <button
        type="button"
        onClick={() => (file ? mutation.mutate() : inputRef.current?.click())}
        className="btn-tab inline-flex h-10 min-w-0 items-center gap-1.5 px-3 py-0"
        title={file ? "Upload access document" : "Choose access document"}
      >
        {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
        <span className="hidden sm:inline">{file ? "Update users" : "Access doc"}</span>
      </button>

      <div className="min-w-0 max-w-[190px] text-xs text-slate-500 sm:max-w-[320px]">
        {mutation.isError ? (
          <div className="flex items-start gap-1.5 text-red-600">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span className="line-clamp-3">{mutation.error instanceof Error ? mutation.error.message : "Upload failed"}</span>
          </div>
        ) : mutation.data ? (
          <div className="space-y-1">
            <div className="flex items-start gap-1.5 text-slate-700">
              <RefreshCw className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#7aa38b]" />
              <span className="line-clamp-3">{mutation.data.message}</span>
            </div>
            <div className="line-clamp-2 text-[11px] text-slate-500">
              {mutation.data.source_filename} • {mutation.data.plantation_codes.join(", ") || "No plantations detected"}
            </div>
          </div>
        ) : file ? (
          <div className="truncate text-slate-700">{file.name}</div>
        ) : (
          <div className="flex items-center gap-1.5">
            <Upload className="h-3.5 w-3.5 shrink-0" />
            <span>Upload user access doc</span>
          </div>
        )}
      </div>
    </div>
  );
}
