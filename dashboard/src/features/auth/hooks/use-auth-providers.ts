import { useEffect, useState } from "react";

/**
 * Which sign-in methods this deployment offers, from the backend's
 * GET /api-gateway/auth/providers on the dashboard's own origin.
 *
 * Until the answer arrives, and whenever the probe fails (for example a
 * deployment that does not route /api-gateway/auth/* to the backend), the
 * dashboard behaves as upstream always has: password sign-in, no Google.
 * One request per page load, shared by every caller.
 */
export type AuthProviders = { google: boolean; password: boolean };

const DEFAULT: AuthProviders = { google: false, password: true };
let pending: Promise<AuthProviders> | null = null;

function load(): Promise<AuthProviders> {
  pending ??= fetch("/api-gateway/auth/providers", { credentials: "omit" })
    .then((res) => (res.ok ? res.json() : null))
    .then((body: { google?: unknown; password?: unknown } | null) => ({
      google: body?.google === true,
      password: body?.password !== false,
    }))
    .catch(() => DEFAULT);
  return pending;
}

/** Test seam: forget the cached answer. */
export function resetAuthProvidersForTests(): void {
  pending = null;
}

export function useAuthProviders(): AuthProviders {
  const [providers, setProviders] = useState<AuthProviders>(DEFAULT);
  useEffect(() => {
    let active = true;
    void load().then((value) => {
      if (active) setProviders(value);
    });
    return () => {
      active = false;
    };
  }, []);
  return providers;
}
