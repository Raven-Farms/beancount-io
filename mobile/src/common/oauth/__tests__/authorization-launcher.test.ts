import { buildAuthorizationUrl } from "../authorization-url";
import {
  createAuthorizationLauncher,
  type AuthorizationBrowserResult,
  type AuthorizationLauncherDependencies,
} from "../authorization-launcher";
import type { PendingOAuthAuthorization } from "../authorization-result";
import type { OAuthDiscovery } from "../discovery";
import type { OAuthSession } from "../session-record";

const issuer = "https://books.example.test";
const discovery: OAuthDiscovery = {
  serverUrl: `${issuer}/`,
  resource: `${issuer}/v1`,
  issuer,
  authorizationEndpoint: `${issuer}/api-gateway/oauth/auth`,
  tokenEndpoint: `${issuer}/api-gateway/oauth/token`,
  revocationEndpoint: `${issuer}/api-gateway/oauth/revoke`,
};
const session: OAuthSession = {
  kind: "oauth",
  serverUrl: `${issuer}/`,
  issuer,
  resource: `${issuer}/v1`,
  tokenEndpoint: discovery.tokenEndpoint,
  revocationEndpoint: discovery.revocationEndpoint,
  clientId: "beancount-mobile",
  userId: "user-1",
  scopes: [
    "openid",
    "offline_access",
    "ledger.read",
    "ledger.write",
    "ledger.admin",
  ],
  tokenType: "Bearer",
  accessToken: "opaque-access",
  accessTokenExpiresAt: Date.now() + 3_600_000,
  refreshToken: "opaque-refresh",
};

type Harness = {
  launch: ReturnType<typeof createAuthorizationLauncher>;
  saved: PendingOAuthAuthorization[];
  stored: { value: PendingOAuthAuthorization | null };
  opened: string[];
  completed: string[];
};

function harness(
  overrides: Partial<AuthorizationLauncherDependencies> = {},
): Harness {
  const saved: PendingOAuthAuthorization[] = [];
  const stored: { value: PendingOAuthAuthorization | null } = { value: null };
  const opened: string[] = [];
  const completed: string[] = [];

  const deps: AuthorizationLauncherDependencies = {
    discover: async () => discovery,
    createPkce: async () => ({
      codeVerifier: "verifier-value",
      codeChallenge: "challenge-value",
    }),
    createState: () => "state-value",
    redirectUri: () => "io.beancount.ios:/oauth/callback",
    savePending: async (pending) => {
      saved.push(pending);
      stored.value = pending;
    },
    loadPending: async () => stored.value,
    clearPending: async () => {
      stored.value = null;
    },
    openAuthSession: async (url) => {
      opened.push(url);
      return {
        type: "success",
        url: "io.beancount.ios:/oauth/callback?code=c&state=state-value",
      } satisfies AuthorizationBrowserResult;
    },
    complete: async (callbackUrl) => {
      completed.push(callbackUrl);
      return session;
    },
    ...overrides,
  };

  return {
    launch: createAuthorizationLauncher(deps),
    saved,
    stored,
    opened,
    completed,
  };
}

// w21/215: changing the server during a stuck discovery left Sign In blocked
// behind the old attempt.
describe("a sign-in dropped while it waits on discovery", () => {
  it("lets the next attempt start fresh and signals the old one to stop", async () => {
    const signals: (AbortSignal | undefined)[] = [];
    let firstAborted = false;
    const { launch, opened } = harness({
      discover: (_serverUrl, signal) => {
        signals.push(signal);
        if (signals.length === 1) {
          return new Promise((_resolve, reject) => {
            signal?.addEventListener("abort", () => {
              firstAborted = true;
              reject(new Error("aborted"));
            });
          });
        }
        return Promise.resolve(discovery);
      },
    });

    const first = launch("https://old.example.test/", "sign_in");
    const firstSettled = first.then(
      () => "resolved",
      () => "rejected",
    );
    launch.abortDiscovery();
    const second = launch(`${issuer}/`, "sign_in");

    expect(await firstSettled).toBe("rejected");
    expect(firstAborted).toBe(true);
    expect(signals.length).toBe(2);
    expect(await second).toBe(session);
    expect(opened.length).toBe(1);
  });

  it("leaves an attempt alone once the browser is open", async () => {
    let release: (value: AuthorizationBrowserResult) => void = () => undefined;
    const { launch } = harness({
      openAuthSession: () =>
        new Promise<AuthorizationBrowserResult>((resolve) => {
          release = resolve;
        }),
    });

    const first = launch(`${issuer}/`, "sign_in");
    await new Promise((resolve) => setTimeout(resolve, 20));
    launch.abortDiscovery();
    // Still the one attempt: a second tap returns it rather than opening another.
    expect(launch(`${issuer}/`, "sign_in")).toBe(first);
    release({ type: "dismiss" });
    expect(await first).toBe(null);
  });
});

describe("native authorization launcher", () => {
  it("persists the verifier before the browser opens", async () => {
    const order: string[] = [];
    const { launch } = harness({
      savePending: async () => {
        order.push("save");
      },
      openAuthSession: async () => {
        order.push("open");
        return { type: "dismiss" };
      },
      loadPending: async () => null,
    });

    await launch(`${issuer}/`, "sign_in");
    expect(order).toEqual(["save", "open"]);
  });

  it("requests code with S256 PKCE, the API resource and the exact redirect", async () => {
    const { launch, opened } = harness();
    await launch(`${issuer}/`, "sign_in");

    const url = new URL(opened[0]);
    expect(url.origin + url.pathname).toBe(discovery.authorizationEndpoint);
    expect(url.searchParams.get("response_type")).toBe("code");
    expect(url.searchParams.get("client_id")).toBe("beancount-mobile");
    expect(url.searchParams.get("code_challenge")).toBe("challenge-value");
    expect(url.searchParams.get("code_challenge_method")).toBe("S256");
    expect(url.searchParams.get("state")).toBe("state-value");
    expect(url.searchParams.get("resource")).toBe(`${issuer}/v1`);
    expect(url.searchParams.get("redirect_uri")).toBe(
      "io.beancount.ios:/oauth/callback",
    );
    expect(url.searchParams.get("scope")).toBe(
      "openid offline_access ledger.read ledger.write ledger.admin",
    );
  });

  it("asks for consent explicitly, which is what keeps offline_access", async () => {
    // Dropping this turns the exchange into an access-token-only response, and
    // the session has nothing to refresh from once the hour is up.
    const { launch, opened } = harness();
    await launch(`${issuer}/`, "sign_in");
    expect(new URL(opened[0]).searchParams.get("prompt")).toBe("consent");
  });

  // w21/153: the first Sign In after a sign-out asks which account to use.
  it("asks for an account choice while the sign-out mark is set", async () => {
    const marked = harness({ chooseAccount: async () => true });
    await marked.launch(`${issuer}/`, "sign_in");
    expect(new URL(marked.opened[0]).searchParams.get("screen_hint")).toBe(
      "select_account",
    );
    const unmarked = harness({ chooseAccount: async () => false });
    await unmarked.launch(`${issuer}/`, "sign_in");
    expect(new URL(unmarked.opened[0]).searchParams.has("screen_hint")).toBe(
      false,
    );
  });

  it("never carries a query the discovered endpoint smuggled in", () => {
    const pending: PendingOAuthAuthorization = {
      ...discovery,
      authorizationEndpoint: `${issuer}/api-gateway/oauth/auth?client_id=evil&redirect_uri=https%3A%2F%2Fevil.test`,
      flow: "sign_in",
      clientId: "beancount-mobile",
      scopes: [...session.scopes],
      redirectUri: "io.beancount.ios:/oauth/callback",
      state: "state-value",
      codeVerifier: "verifier-value",
      createdAt: 0,
    };
    const url = new URL(buildAuthorizationUrl(pending, "challenge-value"));
    expect(url.searchParams.getAll("client_id")).toEqual(["beancount-mobile"]);
    expect(url.searchParams.getAll("redirect_uri")).toEqual([
      "io.beancount.ios:/oauth/callback",
    ]);
  });

  it("completes through the shared completer when the browser returns", async () => {
    const { launch, completed } = harness();
    expect(await launch(`${issuer}/`, "sign_in")).toEqual(session);
    expect(completed).toEqual([
      "io.beancount.ios:/oauth/callback?code=c&state=state-value",
    ]);
  });

  it("creates no session and drops the verifier when the browser is dismissed", async () => {
    const { launch, stored } = harness({
      openAuthSession: async () => ({ type: "cancel" }),
    });
    expect(await launch(`${issuer}/`, "sign_in")).toBe(null);
    expect(stored.value).toBe(null);
  });

  it("keeps a newer request's verifier when an older browser is dismissed", async () => {
    const newer = { state: "newer-state" } as PendingOAuthAuthorization;
    const { launch, stored } = harness({
      openAuthSession: async () => {
        stored.value = newer;
        return { type: "dismiss" };
      },
      loadPending: async () => stored.value,
      clearPending: async () => {
        stored.value = null;
      },
    });
    await launch(`${issuer}/`, "sign_in");
    expect(stored.value).toBe(newer);
  });

  it("opens one browser for concurrent taps", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const { launch, opened } = harness({
      openAuthSession: async (url) => {
        opened.push(url);
        await gate;
        return { type: "dismiss" };
      },
    });

    const first = launch(`${issuer}/`, "sign_in");
    const second = launch(`${issuer}/`, "sign_up");
    expect(second).toBe(first);
    release();
    await first;
    expect(opened.length).toBe(1);
  });

  it("does not open a browser when discovery rejects the server", async () => {
    const { launch, opened, saved } = harness({
      discover: async () => {
        throw new Error("Authorization code flow is unsupported");
      },
    });
    let failure: unknown;
    try {
      await launch(`${issuer}/`, "sign_in");
    } catch (error) {
      failure = error;
    }
    expect(failure instanceof Error).toBeTruthy();
    expect(opened).toEqual([]);
    expect(saved).toEqual([]);
  });
});
