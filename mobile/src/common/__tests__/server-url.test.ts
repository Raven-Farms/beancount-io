describe("server URL utilities", () => {
  let restoreResolveFilename: (() => void) | undefined;
  let validateServerUrl: typeof import("../server-url").validateServerUrl;
  let endpointFor: typeof import("../server-url").endpointFor;
  let testServerConnection: typeof import("../server-url").testServerConnection;
  let isOlderSchema: typeof import("../server-url").isOlderSchema;

  beforeAll(() => {
    const Module = require("module");
    const originalResolveFilename = Module._resolveFilename;
    const configPath = require.resolve("../../config");
    Module._resolveFilename = function patch(
      request: string,
      parent: NodeModule | null | undefined,
      isMain: boolean,
      options?: { paths?: string[] },
    ) {
      if (request === "@/config") {
        return configPath;
      }
      return originalResolveFilename.call(
        this,
        request,
        parent,
        isMain,
        options,
      );
    };
    restoreResolveFilename = () => {
      Module._resolveFilename = originalResolveFilename;
    };

    const modulePath = require.resolve("../server-url");
    delete require.cache[modulePath];
    ({
      validateServerUrl,
      endpointFor,
      testServerConnection,
      isOlderSchema,
    } = require("../server-url"));
  });

  afterAll(() => {
    const modulePath = require.resolve("../server-url");
    delete require.cache[modulePath];
    restoreResolveFilename?.();
  });

  it("normalizes a server URL while preserving a reverse-proxy path prefix", () => {
    expect(validateServerUrl("https://ledger.example.com/beancount")).toEqual({
      ok: true,
      url: "https://ledger.example.com/beancount/",
    });
    expect(
      endpointFor("https://ledger.example.com/beancount/", "api-gateway/"),
    ).toBe("https://ledger.example.com/beancount/api-gateway/");
  });

  it("rejects credentials, query fragments, and insecure remote HTTP", () => {
    expect(validateServerUrl("https://user:pass@ledger.example.com/")).toEqual({
      ok: false,
      code: "credentials",
    });
    expect(
      validateServerUrl("https://ledger.example.com/?token=secret"),
    ).toEqual({
      ok: false,
      code: "query",
    });
    expect(
      validateServerUrl("http://ledger.example.com/", {
        allowInsecureLocalhost: true,
      }),
    ).toEqual({ ok: false, code: "insecure" });
  });

  it("allows HTTP only for explicitly enabled local development", () => {
    expect(
      validateServerUrl("http://localhost:4104/", {
        allowInsecureLocalhost: true,
      }),
    ).toEqual({ ok: true, url: "http://localhost:4104/" });
    expect(
      validateServerUrl("http://127.0.0.1:4104/", {
        allowInsecureLocalhost: false,
      }),
    ).toEqual({ ok: false, code: "insecure" });
  });

  it("allows every loopback spelling, IPv6 included, only when enabled", () => {
    for (const url of [
      "http://localhost:4104/",
      "http://127.0.0.1:4104/",
      "http://[::1]:4104/",
    ]) {
      expect(validateServerUrl(url, { allowInsecureLocalhost: true })).toEqual({
        ok: true,
        url,
      });
      expect(validateServerUrl(url, { allowInsecureLocalhost: false })).toEqual(
        { ok: false, code: "insecure" },
      );
    }
    expect(
      validateServerUrl("http://[2001:db8::1]/", {
        allowInsecureLocalhost: true,
      }),
    ).toEqual({ ok: false, code: "insecure" });
  });

  it("probes health and the complete OAuth discovery contract", async () => {
    const originalFetch = global.fetch;
    const calls: Array<{ url: string; options?: RequestInit }> = [];
    global.fetch = (async (
      url: string | URL | Request,
      options?: RequestInit,
    ) => {
      calls.push({ url: String(url), options });
      const value = String(url);
      if (value.includes("oauth-protected-resource")) {
        return {
          ok: true,
          json: async () => ({
            resource: "https://ledger.example.com/base/v1",
            authorization_servers: ["https://ledger.example.com/base"],
            scopes_supported: ["ledger.read", "ledger.write", "ledger.admin"],
          }),
        } as Response;
      }
      if (value.includes("oauth-authorization-server")) {
        const issuer = "https://ledger.example.com/base";
        return {
          ok: true,
          json: async () => ({
            issuer,
            authorization_endpoint: `${issuer}/api-gateway/oauth/auth`,
            token_endpoint: `${issuer}/api-gateway/oauth/token`,
            revocation_endpoint: `${issuer}/api-gateway/oauth/revoke`,
            userinfo_endpoint: `${issuer}/api-gateway/oauth/me`,
            response_types_supported: ["code"],
            grant_types_supported: ["authorization_code", "refresh_token"],
            scopes_supported: [
              "openid",
              "offline_access",
              "ledger.read",
              "ledger.write",
              "ledger.admin",
            ],
            token_endpoint_auth_methods_supported: ["none"],
            code_challenge_methods_supported: ["S256"],
            authorization_response_iss_parameter_supported: true,
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => ({ data: { health: "OK" } }),
      } as Response;
    }) as typeof fetch;

    try {
      expect(
        await testServerConnection("https://ledger.example.com/base/"),
      ).toEqual({ kind: "connected" });
      expect(calls.map((call) => call.url)).toEqual([
        "https://ledger.example.com/base/api-gateway/",
        "https://ledger.example.com/.well-known/oauth-protected-resource/base/v1",
        "https://ledger.example.com/.well-known/oauth-authorization-server/base",
        // Then the schema probe (w21/593); a server that does not answer it
        // with an introspection result reads as connected.
        "https://ledger.example.com/base/api-gateway/",
      ]);
    } finally {
      global.fetch = originalFetch;
    }
  });

  it("reports a reachable but incompatible server", async () => {
    const originalFetch = global.fetch;
    global.fetch = (async () =>
      ({
        ok: true,
        json: async () => ({ data: { version: "other" } }),
      }) as Response) as typeof fetch;
    try {
      expect(await testServerConnection("https://ledger.example.com/")).toEqual(
        {
          kind: "incompatible",
        },
      );
    } finally {
      global.fetch = originalFetch;
    }
  });

  it("reports timeout and unreachable failures without exposing the URL", async () => {
    const originalFetch = global.fetch;
    global.fetch = ((_url: string | URL | Request, options?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        options?.signal?.addEventListener("abort", () =>
          reject(new Error("aborted")),
        );
      })) as typeof fetch;
    try {
      expect(
        await testServerConnection("https://ledger.example.com/", 1),
      ).toEqual({ kind: "timeout" });
    } finally {
      global.fetch = originalFetch;
    }

    global.fetch = (async () => {
      throw new Error("network unavailable");
    }) as typeof fetch;
    try {
      expect(await testServerConnection("https://ledger.example.com/")).toEqual(
        {
          kind: "unreachable",
        },
      );
    } finally {
      global.fetch = originalFetch;
    }
  });

  // w21/593: "Connected" for a server whose schema lacks what the app selects.
  describe("the schema probe", () => {
    const current = {
      data: {
        errorType: {
          fields: [{ name: "filename" }, { name: "message" }, { name: "hint" }],
        },
        setupType: { name: "LedgerSetupInput" },
      },
    };

    it("reads a current schema as current and a pre-hint or pre-setup one as older", () => {
      expect(isOlderSchema(current)).toBe(false);
      expect(
        isOlderSchema({
          data: {
            errorType: { fields: [{ name: "filename" }, { name: "message" }] },
            setupType: { name: "LedgerSetupInput" },
          },
        }),
      ).toBe(true);
      expect(
        isOlderSchema({
          data: { errorType: current.data.errorType, setupType: null },
        }),
      ).toBe(true);
    });

    it("cannot tell when introspection is off or the answer is odd", () => {
      expect(
        isOlderSchema({ errors: [{ message: "introspection disabled" }] }),
      ).toBe(false);
      expect(isOlderSchema({ data: { errorType: null } })).toBe(false);
      expect(isOlderSchema(null)).toBe(false);
      expect(isOlderSchema("OK")).toBe(false);
    });

    it("turns a reachable server with an older schema into its own result", async () => {
      const originalFetch = global.fetch;
      global.fetch = (async (
        url: string | URL | Request,
        init?: RequestInit,
      ) => {
        const value = String(url);
        const body = String(init?.body ?? "");
        if (value.includes("oauth-protected-resource")) {
          return {
            ok: true,
            json: async () => ({
              resource: "https://ledger.example.com/v1",
              authorization_servers: ["https://ledger.example.com"],
              scopes_supported: ["ledger.read", "ledger.write", "ledger.admin"],
            }),
          } as Response;
        }
        if (value.includes("oauth-authorization-server")) {
          const issuer = "https://ledger.example.com";
          return {
            ok: true,
            json: async () => ({
              issuer,
              authorization_endpoint: `${issuer}/api-gateway/oauth/auth`,
              token_endpoint: `${issuer}/api-gateway/oauth/token`,
              revocation_endpoint: `${issuer}/api-gateway/oauth/revoke`,
              userinfo_endpoint: `${issuer}/api-gateway/oauth/me`,
              response_types_supported: ["code"],
              grant_types_supported: ["authorization_code", "refresh_token"],
              scopes_supported: [
                "openid",
                "offline_access",
                "ledger.read",
                "ledger.write",
                "ledger.admin",
              ],
              token_endpoint_auth_methods_supported: ["none"],
              code_challenge_methods_supported: ["S256"],
              authorization_response_iss_parameter_supported: true,
            }),
          } as Response;
        }
        if (body.includes("ServerSchemaProbe")) {
          return {
            ok: true,
            json: async () => ({
              data: {
                errorType: { fields: [{ name: "message" }] },
                setupType: null,
              },
            }),
          } as Response;
        }
        return {
          ok: true,
          json: async () => ({ data: { health: "OK" } }),
        } as Response;
      }) as typeof fetch;
      try {
        expect(
          await testServerConnection("https://ledger.example.com/"),
        ).toEqual({ kind: "older" });
      } finally {
        global.fetch = originalFetch;
      }
    });
  });
});
