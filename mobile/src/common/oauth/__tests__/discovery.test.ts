import {
  apiResourceForServer,
  discoverOAuthServer,
  OAuthDiscoveryError,
} from "../discovery";

const serverUrl = "https://books.example.test/beancount/";
const issuer = "https://books.example.test/beancount";
const resource = `${issuer}/v1`;

function response(body: object): Response {
  return { ok: true, json: async () => body } as Response;
}

function successfulFetch(calls: string[]): typeof fetch {
  return (async (input: RequestInfo | URL) => {
    const url = String(input);
    calls.push(url);
    if (url.includes("oauth-protected-resource")) {
      return response({
        resource,
        authorization_servers: [issuer],
        scopes_supported: ["ledger.read", "ledger.write", "ledger.admin"],
      });
    }
    return response({
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
    });
  }) as typeof fetch;
}

async function expectFailure(promise: Promise<unknown>): Promise<void> {
  let failed = false;
  try {
    await promise;
  } catch {
    failed = true;
  }
  expect(failed).toBe(true);
}

describe("OAuth discovery", () => {
  it("derives path-aware RFC 9728 and RFC 8414 URLs", async () => {
    const calls: string[] = [];
    const result = await discoverOAuthServer(serverUrl, successfulFetch(calls));

    expect(apiResourceForServer(serverUrl)).toBe(resource);
    expect(calls).toEqual([
      "https://books.example.test/.well-known/oauth-protected-resource/beancount/v1",
      "https://books.example.test/.well-known/oauth-authorization-server/beancount",
    ]);
    expect(result).toEqual({
      serverUrl,
      resource,
      issuer,
      authorizationEndpoint: `${issuer}/api-gateway/oauth/auth`,
      tokenEndpoint: `${issuer}/api-gateway/oauth/token`,
      revocationEndpoint: `${issuer}/api-gateway/oauth/revoke`,
    });
  });

  it("rejects a protected-resource mismatch", async () => {
    const fetcher = (async () =>
      response({
        resource: "https://attacker.example/api",
        authorization_servers: [issuer],
        scopes_supported: ["ledger.read", "ledger.write", "ledger.admin"],
      })) as typeof fetch;
    await expectFailure(discoverOAuthServer(serverUrl, fetcher));
  });

  it("rejects an issuer mismatch before following metadata", async () => {
    const fetcher = (async () =>
      response({
        resource,
        authorization_servers: ["https://beancount.io"],
        scopes_supported: ["ledger.read", "ledger.write", "ledger.admin"],
      })) as typeof fetch;
    await expectFailure(discoverOAuthServer(serverUrl, fetcher));
  });

  // w21/214: every mismatch read as "does not expose the required API", with
  // the address the server names itself by never shown.
  describe("what an incompatible server says that the user can act on", () => {
    const detailOf = async (
      selected: string,
      fetcher: typeof fetch,
    ): Promise<unknown> => {
      try {
        await discoverOAuthServer(selected, fetcher);
        return "resolved";
      } catch (error: unknown) {
        return error instanceof OAuthDiscoveryError ? error.detail : "other";
      }
    };
    const scopes = ["ledger.read", "ledger.write", "ledger.admin"];

    it("offers the address a mismatched server identifies as", async () => {
      // The API address of a deployment whose issuer is the app domain.
      const fetcher = (async () =>
        response({
          resource: "https://app.example.test/v1",
          authorization_servers: ["https://app.example.test"],
          scopes_supported: scopes,
        })) as typeof fetch;
      expect(await detailOf("https://api.example.test/", fetcher)).toEqual({
        reason: "mismatch",
        canonicalUrl: "https://app.example.test/",
      });
    });

    it("offers the issuer when only the authorization server differs", async () => {
      const fetcher = (async () =>
        response({
          resource: "https://api.example.test/v1",
          authorization_servers: ["https://app.example.test"],
          scopes_supported: scopes,
        })) as typeof fetch;
      expect(await detailOf("https://api.example.test/", fetcher)).toEqual({
        reason: "mismatch",
        canonicalUrl: "https://app.example.test/",
      });
    });

    it("offers no address that the app would not accept", async () => {
      for (const claimed of [
        "javascript:alert(1)",
        "http://plain.example.test",
        "https://user:pw@app.example.test",
      ]) {
        const fetcher = (async () =>
          response({
            resource: `${claimed}/v1`,
            authorization_servers: [claimed],
            scopes_supported: scopes,
          })) as typeof fetch;
        expect(await detailOf("https://api.example.test/", fetcher)).toBe(
          undefined,
        );
      }
    });

    it("names a server that is not yet set up for sign-in", async () => {
      const fetcher = (async () =>
        ({
          ok: false,
          status: 503,
          json: async () => ({ error: "oauth_not_configured" }),
        }) as Response) as typeof fetch;
      expect(await detailOf(serverUrl, fetcher)).toEqual({
        reason: "not_configured",
      });
    });

    it("keeps the generic message for a server that is not Beancount.io", async () => {
      const notFound = (async () =>
        ({
          ok: false,
          status: 404,
          json: async () => ({}),
        }) as Response) as typeof fetch;
      expect(await detailOf(serverUrl, notFound)).toBe(undefined);
      const otherUnavailable = (async () =>
        ({
          ok: false,
          status: 503,
          json: async () => ({ error: "maintenance" }),
        }) as Response) as typeof fetch;
      expect(await detailOf(serverUrl, otherUnavailable)).toBe(undefined);
    });
  });

  it("rejects wrong-origin endpoints, implicit flow, and missing S256", async () => {
    for (const mutate of [
      (metadata: Record<string, unknown>) => {
        metadata.token_endpoint = "https://attacker.example/token";
      },
      (metadata: Record<string, unknown>) => {
        metadata.response_types_supported = ["code", "token"];
      },
      (metadata: Record<string, unknown>) => {
        metadata.code_challenge_methods_supported = ["plain"];
      },
    ]) {
      const base = successfulFetch([]);
      let call = 0;
      const fetcher = (async (input: RequestInfo | URL) => {
        const original = await base(input);
        call += 1;
        if (call === 1) return original;
        const metadata = (await original.json()) as Record<string, unknown>;
        mutate(metadata);
        return response(metadata);
      }) as typeof fetch;
      await expectFailure(discoverOAuthServer(serverUrl, fetcher));
    }
  });

  it("tells a dead host apart from a live server that is not Beancount.io", async () => {
    const kindOf = async (fetcher: typeof fetch): Promise<string> => {
      try {
        await discoverOAuthServer(serverUrl, fetcher);
        return "resolved";
      } catch (error: unknown) {
        return error instanceof OAuthDiscoveryError ? error.kind : "other";
      }
    };

    expect(
      await kindOf((async () => {
        throw new TypeError("Network request failed");
      }) as typeof fetch),
    ).toBe("unreachable");
    expect(
      await kindOf(
        (async () =>
          ({ ok: false, json: async () => ({}) }) as Response) as typeof fetch,
      ),
    ).toBe("incompatible");
  });

  it("classifies a non-JSON body from either metadata document as an incompatible server", async () => {
    // A reverse proxy serving its HTML landing page under 200 (w2/029).
    const html = {
      ok: true,
      json: async () => {
        throw new SyntaxError("Unexpected token '<'");
      },
    } as unknown as Response;
    for (const failingDocument of [
      "oauth-protected-resource",
      "oauth-authorization-server",
    ]) {
      const base = successfulFetch([]);
      const fetcher = (async (input: RequestInfo | URL) =>
        String(input).includes(failingDocument)
          ? html
          : base(input)) as typeof fetch;
      let caught: unknown;
      try {
        await discoverOAuthServer(serverUrl, fetcher);
      } catch (error: unknown) {
        caught = error;
      }
      expect(caught instanceof OAuthDiscoveryError).toBe(true);
      expect((caught as OAuthDiscoveryError).kind).toBe("incompatible");
    }
  });

  it("classifies a missing, malformed, or off-issuer endpoint as an incompatible server", async () => {
    for (const endpoint of [
      undefined,
      "not a url",
      "https://attacker.example/token",
    ]) {
      const base = successfulFetch([]);
      const fetcher = (async (input: RequestInfo | URL) => {
        const original = await base(input);
        if (!String(input).includes("oauth-authorization-server"))
          return original;
        const metadata = (await original.json()) as Record<string, unknown>;
        metadata.token_endpoint = endpoint;
        return response(metadata);
      }) as typeof fetch;
      let caught: unknown;
      try {
        await discoverOAuthServer(serverUrl, fetcher);
      } catch (error: unknown) {
        caught = error;
      }
      expect(caught instanceof OAuthDiscoveryError).toBe(true);
      expect((caught as OAuthDiscoveryError).kind).toBe("incompatible");
    }
  });
});
