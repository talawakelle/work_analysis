import { FormEvent, useState } from "react";
import { AlertCircle, LockKeyhole, LogIn, UserRound } from "lucide-react";

type Props = {
  onSubmit: (username: string, password: string) => Promise<void> | void;
  loading?: boolean;
  error?: string | null;
};

export default function LoginPanel({ onSubmit, loading = false, error }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit(username.trim(), password);
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-4xl items-center justify-center px-3 py-6 sm:px-4">
      <section className="panel w-full max-w-lg p-4 sm:p-6">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl bg-emerald-50 p-3 text-emerald-700">
            <LockKeyhole className="h-5 w-5" />
          </div>
          <div>
            <div className="text-xl font-semibold text-slate-800">Estate Login</div>
            <div className="mt-1 text-sm text-slate-500">
              Enter your username and password to open the correct estate scope. Estate users see one estate, CEO users see their plantation estates, MD sees all plantations, and ADMIN can upload datasets and access documents.
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 space-y-3">
          <label className="soft-block block p-3">
            <div className="eyebrow">Username</div>
            <div className="mt-2 flex items-center gap-2">
              <UserRound className="h-4 w-4 text-slate-500" />
              <input
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Example: TTEL@LG or ADMIN"
                className="w-full bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
              />
            </div>
          </label>

          <label className="soft-block block p-3">
            <div className="eyebrow">Password</div>
            <div className="mt-2 flex items-center gap-2">
              <LockKeyhole className="h-4 w-4 text-slate-500" />
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter password"
                className="w-full bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
              />
            </div>
          </label>

          {error ? (
            <div className="flex items-start gap-2 rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : null}

          <button
            type="submit"
            disabled={loading}
            className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[#86b39a] px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-70"
          >
            <LogIn className="h-4 w-4" />
            {loading ? "Checking account..." : "Sign in"}
          </button>
        </form>

        <div className="mt-4 rounded-2xl bg-slate-50 px-3 py-3 text-xs text-slate-500">
          This screen matches your username and password, then locks the dashboard to the correct estate, plantation, or executive scope.
        </div>
      </section>
    </div>
  );
}
