export type AuthIdentity = {
  username: string | null;
  source: string;
};

export type AuthSession = {
  username: string;
  display_name?: string | null;
  resolved_estate?: string | null;
  role?: string;
};

const QUERY_KEYS = ["username", "user", "email", "login"];
const STORAGE_KEYS = [
  "estate.workforce.auth",
  "estate.workforce.user",
  "authUser",
  "auth.user",
  "auth",
  "userAuth",
  "userSession",
  "currentUser",
  "current_user",
  "loggedInUser",
  "username",
  "user",
  "loginUser",
  "profile",
];

function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key) || window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // ignore storage failures
  }
}

function removeStorage(key: string) {
  try {
    window.localStorage.removeItem(key);
    window.sessionStorage.removeItem(key);
  } catch {
    // ignore storage failures
  }
}

function extractUsernameFromUnknown(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return null;

    if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
      try {
        return extractUsernameFromUnknown(JSON.parse(trimmed));
      } catch {
        return trimmed;
      }
    }

    return trimmed;
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const resolved = extractUsernameFromUnknown(item);
      if (resolved) return resolved;
    }
    return null;
  }

  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const candidateKeys = [
      "username",
      "userName",
      "user_name",
      "login",
      "email",
      "user",
      "currentUser",
      "current_user",
      "authUser",
      "auth_user",
      "name",
    ];

    for (const key of candidateKeys) {
      const resolved = extractUsernameFromUnknown(record[key]);
      if (resolved) return resolved;
    }
  }

  return null;
}

export function getStoredAuthSession(): AuthSession | null {
  if (typeof window === "undefined") return null;
  const raw = readStorage("estate.workforce.auth");
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<AuthSession>;
    if (!parsed.username || typeof parsed.username !== "string") return null;
    return {
      username: parsed.username,
      display_name: parsed.display_name ?? null,
      resolved_estate: parsed.resolved_estate ?? null,
      role: parsed.role ?? "viewer",
    };
  } catch {
    const username = extractUsernameFromUnknown(raw);
    return username ? { username } : null;
  }
}

export function setStoredAuthSession(session: AuthSession) {
  if (typeof window === "undefined") return;
  writeStorage("estate.workforce.auth", JSON.stringify(session));
  writeStorage("estate.workforce.user", session.username);
}

export function clearStoredAuthSession() {
  if (typeof window === "undefined") return;
  removeStorage("estate.workforce.auth");
  removeStorage("estate.workforce.user");
}

export function getAuthIdentity(): AuthIdentity {
  if (typeof window === "undefined") {
    return { username: null, source: "server" };
  }

  const params = new URLSearchParams(window.location.search);
  for (const key of QUERY_KEYS) {
    const value = params.get(key)?.trim();
    if (value) {
      return { username: value, source: `query:${key}` };
    }
  }

  const session = getStoredAuthSession();
  if (session?.username) {
    return { username: session.username, source: "storage:estate.workforce.auth" };
  }

  for (const key of STORAGE_KEYS) {
    const raw = readStorage(key);
    const value = extractUsernameFromUnknown(raw);
    if (value) {
      return { username: value, source: `storage:${key}` };
    }
  }

  const globalCandidates = [
    (window as Window & { __AUTH_USER__?: unknown }).__AUTH_USER__,
    (window as Window & { __USER__?: unknown }).__USER__,
    (window as Window & { currentUser?: unknown }).currentUser,
  ];

  for (const candidate of globalCandidates) {
    const value = extractUsernameFromUnknown(candidate);
    if (value) {
      return { username: value, source: "window" };
    }
  }

  return { username: null, source: "anonymous" };
}

export function persistAuthIdentity() {
  if (typeof window === "undefined") return;

  const identity = getAuthIdentity();
  if (!identity.username) return;

  const existing = getStoredAuthSession();
  if (!existing?.username) {
    setStoredAuthSession({ username: identity.username });
  } else {
    writeStorage("estate.workforce.user", identity.username);
  }
}
