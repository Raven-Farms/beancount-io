import { createHash } from "node:crypto";
import http from "node:http";
import type { AddressInfo } from "node:net";
import Koa from "koa";
import Router from "@koa/router";
import { setGoogleAuthRoutes } from "../google-auth-routes";
import type {
  GoogleCeremonyRecord,
  GoogleStateStore,
} from "@/features/auth/google/google-state-store";
import { ForbiddenError } from "@/shared/errors";
import {
  CLIENT_ID,
  googleTestKeys,
} from "@/features/auth/google/__tests__/google-test-keys";

const DASHBOARD = "https://books.example.com";

/** In-memory store with the same one-time semantics as the Redis one. */
function memoryStore(): GoogleStateStore & {
  records: Map<string, GoogleCeremonyRecord>;
} {
  const records = new Map<string, GoogleCeremonyRecord>();
  return {
    records,
    async put(state, record) {
      records.set(state, record);
    },
    async consume(state) {
      const r = records.get(state) ?? null;
      records.delete(state);
      return r;
    },
  };
}

async function setup(
  opts: {
    google?: boolean;
    passwordAuthEnabled?: boolean;
    signIn?: jest.Mock;
    tokenResponse?: (nonce: string) => Promise<Response>;
  } = {},
) {
  const t = await googleTestKeys();
  const store = memoryStore();
  const signInWithGoogle =
    opts.signIn ??
    jest.fn().mockResolvedValue({
      token: "session-token",
      expireAt: new Date(Date.now() + 3_600_000),
    });
  let lastNonce = "";
  // Challenges sent to Google at /start; like Google, the fake token endpoint
  // refuses a code exchange whose verifier does not hash to one of them.
  const challenges = new Set<string>();
  const fetch = jest.fn(
    async (_url: string, init: { body: URLSearchParams }) => {
      const verifier =
        new URLSearchParams(init.body).get("code_verifier") ?? "";
      const challenge = createHash("sha256")
        .update(verifier)
        .digest("base64url");
      if (!challenges.has(challenge)) {
        return new Response(JSON.stringify({ error: "invalid_grant" }), {
          status: 400,
        });
      }
      return opts.tokenResponse
        ? opts.tokenResponse(lastNonce)
        : new Response(
            JSON.stringify({ id_token: await t.sign({ nonce: lastNonce }) }),
            {
              status: 200,
            },
          );
    },
  );
  const router = new Router();
  setGoogleAuthRoutes(router, {
    authSession: { signInWithGoogle },
    config: {
      env: "production",
      passwordAuthEnabled: opts.passwordAuthEnabled ?? true,
      dashboard: { url: DASHBOARD },
      jwt: { secret: "x", expMins: 60, cookieDomain: null },
      googleAuth:
        opts.google === false
          ? null
          : {
              clientId: CLIENT_ID,
              clientSecret: "test-secret",
              hostedDomains: new Set(["example.com"]),
            },
    } as never,
    stateStore: {
      put: async (s, r) => {
        lastNonce = r.nonce;
        return store.put(s, r);
      },
      consume: (s) => store.consume(s),
    },
    oidc: () => ({ fetch: fetch as never, keys: t.keys }),
  });
  const app = new Koa();
  app.use(router.routes());
  const server = http.createServer(app.callback());
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  const get = (path: string, cookie?: string) =>
    fetch === undefined
      ? Promise.reject()
      : globalThis.fetch(base + path, {
          redirect: "manual",
          headers: cookie ? { cookie } : {},
        });
  return { server, base, get, store, signInWithGoogle, fetch, challenges };
}

const location = (res: Response) =>
  new URL(res.headers.get("location") ?? "", DASHBOARD);
const reasonOf = (res: Response) => location(res).searchParams.get("reason");
const stateCookieOf = (res: Response) =>
  (res.headers.get("set-cookie") ?? "").match(/bcio_google_state=([^;]+)/)?.[1];

async function start(
  s: Awaited<ReturnType<typeof setup>>,
  next = "/ledger/pat",
) {
  const res = await s.get(
    `/api-gateway/auth/google/start?next=${encodeURIComponent(next)}`,
  );
  const state = location(res).searchParams.get("state") ?? "";
  s.challenges.add(location(res).searchParams.get("code_challenge") ?? "");
  return { res, state, cookie: `bcio_google_state=${stateCookieOf(res)}` };
}

describe("Google sign-in routes", () => {
  let s: Awaited<ReturnType<typeof setup>>;
  afterEach(async () => {
    await new Promise((resolve) => s.server.close(resolve));
  });

  it("reports whether Google is offered", async () => {
    s = await setup();
    expect(await (await s.get("/api-gateway/auth/providers")).json()).toEqual({
      google: true,
      password: true,
    });
    await new Promise((resolve) => s.server.close(resolve));
    s = await setup({ google: false });
    expect(await (await s.get("/api-gateway/auth/providers")).json()).toEqual({
      google: false,
      password: true,
    });
  });

  it("reports password sign-in as off when AUTH_PASSWORD_ENABLED is false", async () => {
    s = await setup({ passwordAuthEnabled: false });
    expect(await (await s.get("/api-gateway/auth/providers")).json()).toEqual({
      google: true,
      password: false,
    });
  });

  it("start sends the browser to Google with state bound to a cookie", async () => {
    s = await setup();
    const { res, state } = await start(s);
    expect(res.status).toBe(302);
    expect(location(res).origin).toBe("https://accounts.google.com");
    expect(res.headers.get("cache-control")).toBe("no-store");
    const cookie = res.headers.get("set-cookie") ?? "";
    expect(cookie).toMatch(/bcio_google_state=/);
    expect(cookie).toMatch(/path=\/api-gateway\/auth\/google/i);
    expect(cookie).toMatch(/httponly/i);
    expect(cookie).toMatch(/samesite=lax/i);
    expect(s.store.records.get(state)).toMatchObject({ next: "/ledger/pat" });
  });

  it.each([
    "https://evil.example/x",
    "//evil.example",
    "/%09/evil.example",
    "/\\evil.example",
  ])("start stores / instead of the unsafe next %j", async (next) => {
    s = await setup();
    const { state } = await start(s, next);
    expect(s.store.records.get(state)?.next).toBe("/");
  });

  it("start reports google_unavailable when Google is not configured", async () => {
    s = await setup({ google: false });
    const res = await s.get("/api-gateway/auth/google/start");
    expect(reasonOf(res)).toBe("google_unavailable");
    expect(s.store.records.size).toBe(0);
  });

  it("completes: session cookie (host-only) and back to next", async () => {
    s = await setup();
    const { state, cookie } = await start(s);
    const res = await s.get(
      `/api-gateway/auth/google/callback?state=${state}&code=c`,
      cookie,
    );
    expect(res.status).toBe(302);
    expect(location(res).toString()).toBe(`${DASHBOARD}/ledger/pat`);
    const setCookie = res.headers.get("set-cookie") ?? "";
    expect(setCookie).toMatch(/authSess:beancount\.io=session-token/);
    expect(setCookie).not.toMatch(/authSess[^,]*domain=/i);
    expect(setCookie).toMatch(/bcio_google_state=;/);
    expect(s.signInWithGoogle).toHaveBeenCalledWith(
      expect.objectContaining({
        email: "pat@example.com",
        hostedDomain: "example.com",
      }),
      expect.any(String),
    );
    expect(s.store.records.size).toBe(0);
  });

  it("fails when the verifier does not match the challenge sent to Google", async () => {
    s = await setup();
    const { state, cookie } = await start(s);
    s.challenges.clear(); // Google would only know a different challenge
    const res = await s.get(
      `/api-gateway/auth/google/callback?state=${state}&code=c`,
      cookie,
    );
    expect(reasonOf(res)).toBe("google_failed");
    expect(res.headers.get("set-cookie") ?? "").not.toMatch(/authSess/);
  });

  it("refuses a callback without the state cookie and spends nothing", async () => {
    s = await setup();
    const { state } = await start(s);
    const res = await s.get(
      `/api-gateway/auth/google/callback?state=${state}&code=c`,
    );
    expect(reasonOf(res)).toBe("google_state");
    expect(s.store.records.has(state)).toBe(true);
    expect(s.fetch).not.toHaveBeenCalled();
  });

  it("refuses a state that does not match the cookie", async () => {
    s = await setup();
    const a = await start(s);
    const b = await start(s);
    const res = await s.get(
      `/api-gateway/auth/google/callback?state=${a.state}&code=c`,
      b.cookie,
    );
    expect(reasonOf(res)).toBe("google_state");
    expect(s.fetch).not.toHaveBeenCalled();
  });

  it("redeems a state only once", async () => {
    s = await setup();
    const { state, cookie } = await start(s);
    await s.get(
      `/api-gateway/auth/google/callback?state=${state}&code=c`,
      cookie,
    );
    const again = await s.get(
      `/api-gateway/auth/google/callback?state=${state}&code=c`,
      cookie,
    );
    expect(reasonOf(again)).toBe("google_state");
    expect(s.signInWithGoogle).toHaveBeenCalledTimes(1);
  });

  it("reports a cancelled consent and keeps next", async () => {
    s = await setup();
    const { state, cookie } = await start(s);
    const res = await s.get(
      `/api-gateway/auth/google/callback?state=${state}&error=access_denied`,
      cookie,
    );
    expect(reasonOf(res)).toBe("google_cancelled");
    expect(location(res).searchParams.get("next")).toBe("/ledger/pat");
    expect(s.fetch).not.toHaveBeenCalled();
  });

  it.each([
    [
      "signup not allowed",
      new ForbiddenError("no", "signup"),
      "google_not_allowed",
    ],
    ["blocked user", new ForbiddenError("banned", "user"), "google_blocked"],
    ["unexpected failure", new Error("db down"), "google_failed"],
  ])(
    "maps %s to a reason and sets no session",
    async (_label, error, expected) => {
      s = await setup({ signIn: jest.fn().mockRejectedValue(error) });
      const { state, cookie } = await start(s);
      const res = await s.get(
        `/api-gateway/auth/google/callback?state=${state}&code=c`,
        cookie,
      );
      expect(reasonOf(res)).toBe(expected);
      expect(res.headers.get("set-cookie") ?? "").not.toMatch(/authSess/);
    },
  );

  it("maps a refused identity to its reason without leaking the code", async () => {
    const t = await googleTestKeys();
    s = await setup({
      tokenResponse: async (nonce) =>
        new Response(JSON.stringify({ id_token: await t.sign({ nonce }) }), {
          status: 200,
        }),
    });
    // Signed by a key the routes do not trust (setup made its own keys).
    const { state, cookie } = await start(s);
    const res = await s.get(
      `/api-gateway/auth/google/callback?state=${state}&code=supersecretcode`,
      cookie,
    );
    expect(reasonOf(res)).toBe("google_failed");
    expect(res.headers.get("location")).not.toMatch(/supersecretcode/);
    expect(res.headers.get("set-cookie") ?? "").not.toMatch(/authSess/);
  });
});
