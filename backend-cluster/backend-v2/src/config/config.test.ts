import {
  assertOAuthInteractionHost,
  config,
  getDevelopmentPremiumUserIds,
  getMcpRegistryAuthProof,
  getOAuthPublicUrl,
  parseCookieDomain,
  parseCorsAllowedOrigins,
  parseSignupAllowedDomains,
  parseSignupAllowedEmails,
} from "./config";

describe("config", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  it("should have correct default values", () => {
    expect(config.project).toBe("beancount-io");
    expect(config.jwt.expMins).toBe(525600);
    expect(config.analytics.gaMeasurementId).toBe("G-94TFG6X2Q5");
  });

  it("should read env from NODE_ENV", () => {
    // Jest sets NODE_ENV to "test" by default, and config now recognizes
    // "development", "test", and "production"
    expect(config.env).toBe("test");
  });

  it("should have correct server defaults", () => {
    expect(config.server.proxy).toBe(true);
    expect(config.server.port).toBe(4104);
  });

  it("limits local premium-user overrides to development", () => {
    expect(
      getDevelopmentPremiumUserIds(" user-a, user-b,user-a ", "development"),
    ).toEqual(new Set(["user-a", "user-b"]));
    expect(getDevelopmentPremiumUserIds("user-a", "production")).toEqual(
      new Set(),
    );
    expect(getDevelopmentPremiumUserIds("user-a", "test")).toEqual(new Set());
  });

  it("should have correct logger defaults", () => {
    expect(config.logger.enabled).toBe(true);
    expect(config.logger.level).toBe("debug");
  });

  it("should have correct gitea defaults", () => {
    expect(config.gitea.hostname).toBe("git.beancount.io");
    expect(config.gitea.httpPort).toBe(3000);
    expect(config.gitea.sshPort).toBe(2222);
  });

  it("should have correct dashboard URL default", () => {
    expect(config.dashboard.url).toBe("https://beancount.io");
  });

  describe("OAuth public URL validation", () => {
    it("normalizes a path-prefixed HTTPS issuer", () => {
      expect(
        getOAuthPublicUrl(
          "https://books.example.test/beancount/",
          "https://beancount.io",
          "OAUTH_ISSUER",
          "production",
        ),
      ).toBe("https://books.example.test/beancount");
    });

    it.each([
      "",
      "not a url",
      "https://user@example.test",
      "https://example.test?a=1",
    ])("rejects malformed or ambiguous value %p", (value) => {
      expect(() =>
        getOAuthPublicUrl(
          value,
          "https://beancount.io",
          "OAUTH_ISSUER",
          "production",
        ),
      ).toThrow(Error);
    });

    it("permits cleartext only for loopback development", () => {
      expect(
        getOAuthPublicUrl(
          "http://localhost:42601",
          "https://beancount.io",
          "OAUTH_ISSUER",
          "development",
        ),
      ).toBe("http://localhost:42601");
      expect(() =>
        getOAuthPublicUrl(
          "http://books.example.test",
          "https://beancount.io",
          "OAUTH_ISSUER",
          "development",
        ),
      ).toThrow(Error);
      expect(() =>
        getOAuthPublicUrl(
          "http://localhost:42601",
          "https://beancount.io",
          "OAUTH_ISSUER",
          "production",
        ),
      ).toThrow(Error);
    });

    it("requires interaction pages to share the issuer hostname", () => {
      expect(() =>
        assertOAuthInteractionHost(
          "http://localhost:42601",
          "http://localhost:42600",
        ),
      ).not.toThrow();
      expect(() =>
        assertOAuthInteractionHost(
          "https://auth.example.test",
          "https://dashboard.example.test",
        ),
      ).toThrow(Error);
    });
  });

  describe("gitea configuration structure", () => {
    it("should have internalHostname property", () => {
      expect(config.gitea).toHaveProperty("internalHostname");
      expect(typeof config.gitea.internalHostname).toBe("string");
    });

    it("should have hostname property", () => {
      expect(config.gitea).toHaveProperty("hostname");
      expect(typeof config.gitea.hostname).toBe("string");
    });

    it("should have httpPort property", () => {
      expect(config.gitea).toHaveProperty("httpPort");
      expect(typeof config.gitea.httpPort).toBe("number");
      expect(config.gitea.httpPort).toBeGreaterThan(0);
    });

    it("should have sshPort property", () => {
      expect(config.gitea).toHaveProperty("sshPort");
      expect(typeof config.gitea.sshPort).toBe("number");
      expect(config.gitea.sshPort).toBeGreaterThan(0);
    });

    it("should have externalHttpPort property", () => {
      expect(config.gitea).toHaveProperty("externalHttpPort");
      expect(typeof config.gitea.externalHttpPort).toBe("number");
      expect(config.gitea.externalHttpPort).toBeGreaterThan(0);
    });

    it("should have valid port numbers", () => {
      expect(config.gitea.httpPort).toBeLessThanOrEqual(65535);
      expect(config.gitea.externalHttpPort).toBeLessThanOrEqual(65535);
      expect(config.gitea.sshPort).toBeLessThanOrEqual(65535);
    });
  });

  describe("plaid configuration", () => {
    it("should have correct default environment", () => {
      expect(config.plaid.environment).toBe("sandbox");
    });

    it("should have valid environment value", () => {
      const validEnvironments = ["sandbox", "development", "production"];
      expect(validEnvironments).toContain(config.plaid.environment);
    });

    it("should have plaid properties", () => {
      expect(config.plaid).toHaveProperty("clientId");
      expect(config.plaid).toHaveProperty("secret");
      expect(config.plaid).toHaveProperty("environment");
      expect(config.plaid).toHaveProperty("webhookUrl");
    });

    it("should have correct plaid property types", () => {
      expect(typeof config.plaid.clientId).toBe("string");
      expect(typeof config.plaid.secret).toBe("string");
      expect(typeof config.plaid.environment).toBe("string");
      expect(typeof config.plaid.webhookUrl).toBe("string");
    });
  });

  describe("MCP Registry domain proof", () => {
    const ed25519 =
      "v=MCPv1; k=ed25519; p=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
    const ecdsaP384 =
      "v=MCPv1; k=ecdsap384; p=AgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==";

    it("is unset by default so a self-host serves no proof", () => {
      expect(config.mcpRegistry.authProof).toBeNull();
      expect(getMcpRegistryAuthProof(undefined)).toBeNull();
      expect(getMcpRegistryAuthProof("")).toBeNull();
      expect(getMcpRegistryAuthProof("   ")).toBeNull();
    });

    it("accepts the whole record for either supported algorithm", () => {
      expect(getMcpRegistryAuthProof(ed25519)).toBe(ed25519);
      expect(getMcpRegistryAuthProof(ecdsaP384)).toBe(ecdsaP384);
      // Surrounding whitespace from an env file is not part of the record.
      expect(getMcpRegistryAuthProof(`  ${ed25519}\n`)).toBe(ed25519);
    });

    it("refuses anything that is not the record mcp-publisher emits", () => {
      const expectRefused = (value: string) =>
        expect(() => getMcpRegistryAuthProof(value)).toThrow(
          /MCP_REGISTRY_AUTH_PROOF must be the whole proof record/,
        );
      // A bare key: the operator pasted `p=` without the envelope.
      expectRefused("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=");
      // Wrong version, unknown algorithm, non-base64 key, trailing junk.
      expectRefused(ed25519.replace("MCPv1", "MCPv2"));
      expectRefused(ed25519.replace("ed25519", "rsa"));
      expectRefused("v=MCPv1; k=ed25519; p=not base64!");
      expectRefused(`${ed25519}; extra=1`);
    });
  });

  describe("parseCookieDomain (AUTH_COOKIE_DOMAIN)", () => {
    it("is undefined when unset or blank (managed default)", () => {
      expect(parseCookieDomain(undefined)).toBeUndefined();
      expect(parseCookieDomain("  ")).toBeUndefined();
    });

    it("is null for host-only", () => {
      expect(parseCookieDomain("host-only")).toBeNull();
    });

    it("passes an explicit domain through", () => {
      expect(parseCookieDomain(" .Example.com ")).toBe(".example.com");
      expect(parseCookieDomain("books.example.com")).toBe("books.example.com");
    });

    it("rejects anything that is not a bare domain at boot", () => {
      for (const bad of [
        "https://example.com",
        "example.com:443",
        "example.com/path",
        ".example.com; SameSite=None",
        "localhost",
        "..example.com",
      ]) {
        expect(() => parseCookieDomain(bad)).toThrow(/AUTH_COOKIE_DOMAIN/);
      }
    });
  });

  describe("parseCorsAllowedOrigins (CORS_ALLOWED_ORIGINS)", () => {
    it("is empty when unset", () => {
      expect(parseCorsAllowedOrigins(undefined).size).toBe(0);
    });

    it("normalizes entries to origins", () => {
      const origins = parseCorsAllowedOrigins(
        "https://Books.Example.com/, https://app.example.com:8443, http://[::1]:3000",
      );
      expect([...origins]).toEqual([
        "https://books.example.com",
        "https://app.example.com:8443",
        "http://[::1]:3000",
      ]);
    });

    it("rejects malformed or non-http entries at boot", () => {
      expect(() => parseCorsAllowedOrigins("not a url")).toThrow();
      expect(() => parseCorsAllowedOrigins("books.example.com")).toThrow(
        /unsupported origin/,
      );
      expect(() => parseCorsAllowedOrigins("ftp://example.com")).toThrow(
        /unsupported origin/,
      );
      for (const bad of [
        "https://example.com/path",
        "https://user:pw@example.com",
        "https://example.com/?q=1",
        "https://example.com/path/..",
        "https://example.com/?",
        "https://example.com/#",
        "https://*.example.com",
        "https://example.com:99999x",
      ]) {
        expect(() => parseCorsAllowedOrigins(bad)).toThrow(/not a bare origin/);
      }
    });
  });

  describe("parseSignupAllowedEmails / parseSignupAllowedDomains", () => {
    it("are empty when unset (open signup)", () => {
      expect(parseSignupAllowedEmails(undefined).size).toBe(0);
      expect(parseSignupAllowedDomains(" ").size).toBe(0);
      expect(config.signup.allowedEmails.size).toBe(0);
      expect(config.signup.allowedDomains.size).toBe(0);
    });

    it("lowercase and trim entries", () => {
      expect([
        ...parseSignupAllowedEmails(" CPA@Firm.Example , a@b.co"),
      ]).toEqual(["cpa@firm.example", "a@b.co"]);
      expect([...parseSignupAllowedDomains("Example.com, b.co")]).toEqual([
        "example.com",
        "b.co",
      ]);
    });

    it("reject malformed entries at boot", () => {
      for (const bad of [
        "not-an-email",
        "@example.com",
        "a@",
        "a b@example.com",
        "a@localhost",
      ]) {
        expect(() => parseSignupAllowedEmails(bad)).toThrow(
          /SIGNUP_ALLOWED_EMAILS/,
        );
      }
      for (const bad of [
        "@example.com",
        "*.example.com",
        "example",
        "https://example.com",
        "a@example.com",
      ]) {
        expect(() => parseSignupAllowedDomains(bad)).toThrow(
          /SIGNUP_ALLOWED_DOMAINS/,
        );
      }
    });
  });
});
