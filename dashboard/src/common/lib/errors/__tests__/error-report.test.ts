import { describe, it, expect } from "vitest";
import { formatErrorReport } from "../error-report";

const base = {
  url: "https://beancount.io/ledger/a/b/balance-sheet",
  userAgent: "TestBrowser/1.0",
  time: new Date("2026-10-07T12:00:00.000Z"),
};

describe("formatErrorReport", () => {
  it("identifies the failure, the page, the time, and the browser", () => {
    const error = new TypeError("x is not a function");
    error.stack = "TypeError: x is not a function\n    at render (a.js:1:2)";
    const report = formatErrorReport({
      ...base,
      error,
      componentStack: "\n    at BalanceSheet\n    at Outlet",
    });

    expect(report).toContain("TypeError: x is not a function");
    expect(report).toContain(
      "URL: https://beancount.io/ledger/a/b/balance-sheet",
    );
    expect(report).toContain("Time: 2026-10-07T12:00:00.000Z");
    expect(report).toContain("Browser: TestBrowser/1.0");
    expect(report).toContain("at render (a.js:1:2)");
    expect(report).toContain("at BalanceSheet");
  });

  it("truncates a long stack", () => {
    const error = new Error("deep");
    error.stack = Array.from({ length: 50 }, (_, i) => `    at f${i}`).join(
      "\n",
    );
    const report = formatErrorReport({ ...base, error });

    expect(report).toContain("at f19");
    expect(report).not.toContain("at f20");
    expect(report).toContain("…");
  });

  it("describes a thrown non-error", () => {
    expect(formatErrorReport({ ...base, error: "boom" })).toContain(
      "Error: boom",
    );
  });

  it("keeps the recovery page and useful failure context without its private link", () => {
    const challenge = `rcv_${"a1".repeat(32)}`;
    const url = `https://beancount.io/auth/login?recovery=${challenge}&next=%2Fledger%23activity`;
    const error = new TypeError(`Unable to render recovery ${challenge}`);
    error.stack = `TypeError: ${error.message}\n    at RecoveryForm (login.js:4:2)`;

    const report = formatErrorReport({
      ...base,
      url,
      error,
      componentStack: `\n    at RecoveryForm (${url})\n    at Outlet`,
    });

    expect(report).not.toContain(challenge);
    expect(report).toContain("URL: https://beancount.io/auth/login\n");
    expect(report).toContain("TypeError: Unable to render recovery");
    expect(report).toContain("at RecoveryForm (login.js:4:2)");
    expect(report).toContain("at Outlet");
    expect(report).toContain("Time: 2026-10-07T12:00:00.000Z");
    expect(report).toContain("Browser: TestBrowser/1.0");
  });

  it.each([
    ["/auth/reset-password?token=", "synthetic-reset-token"],
    ["/auth/callback?oneTimeToken=", "synthetic-one-time-token"],
    ["/oauth/callback?code=", "synthetic-oauth-code"],
    ["/oauth/callback?state=", "synthetic-oauth-state"],
    ["/auth/login#access_token=", "synthetic-access-token"],
    ["/auth/login#/callback?refresh_token=", "synthetic-refresh-token"],
    ["/auth/login?id_token=", "synthetic-id-token"],
    ["/auth/login?code_verifier=", "synthetic-code-verifier"],
    ["/auth/login?password=", "synthetic pass+/密碼"],
  ])(
    "redacts credentials from %s and their unlabelled echoes",
    (path, value) => {
      const encoded = encodeURIComponent(value);
      const formEncoded = new URLSearchParams({ value }).toString().slice(6);
      const error = new Error(
        `Authentication failed for ${value} / ${encoded}`,
      );
      error.name = `Failure ${value}`;
      error.stack = `Failure: ${formEncoded}\n    at callback (auth.js:2:3)`;

      const report = formatErrorReport({
        ...base,
        url: `https://beancount.io${path}${encoded}`,
        error,
        userAgent: `TestBrowser/1.0 ${value}`,
        componentStack: `\n    at LoginForm ${encoded.toLowerCase()}`,
      });

      for (const secret of [value, encoded, encoded.toLowerCase(), formEncoded])
        expect(report).not.toContain(secret);
      expect(report).toContain("Authentication failed");
      expect(report).toContain("at callback (auth.js:2:3)");
      expect(report).toContain("[REDACTED]");
    },
  );

  it("omits URL credentials, harmless query filters and fragments while retaining the path", () => {
    const report = formatErrorReport({
      ...base,
      url: "https://synthetic-user:synthetic-url-password@beancount.io/ledger/alice/main?period=2026#activity",
      error: "Could not load ledger: synthetic-url-password",
    });

    expect(report).toContain("URL: https://beancount.io/ledger/alice/main\n");
    for (const omitted of [
      "synthetic-user",
      "synthetic-url-password",
      "period=2026",
      "#activity",
    ])
      expect(report).not.toContain(omitted);
    expect(report).toContain("Could not load ledger");
  });

  it("keeps malformed URL userinfo from disabling other credential redactions", () => {
    const report = formatErrorReport({
      ...base,
      url: "https://%FF:synthetic-userinfo-password@beancount.io/auth/reset-password?token=synthetic-reset-token",
      error:
        "Render failed for synthetic-reset-token and synthetic-userinfo-password",
    });

    expect(report).not.toContain("synthetic-reset-token");
    expect(report).not.toContain("synthetic-userinfo-password");
    expect(report).toContain("URL: https://beancount.io/auth/reset-password");
  });

  it("masks recognizable challenges and labelled credentials even away from the current URL", () => {
    const challenge = `rcv_${"bc".repeat(32)}`;
    const report = formatErrorReport({
      ...base,
      error: `Recovery ${challenge}; token=synthetic-token; {"password":"synthetic spaced password"}; Authorization: Bearer synthetic-bearer`,
      componentStack:
        "\n    at Auth (callback.js?oneTimeToken=synthetic-callback:1:2)",
    });

    for (const secret of [
      challenge,
      "synthetic-token",
      "synthetic spaced password",
      "synthetic-bearer",
      "synthetic-callback",
    ])
      expect(report).not.toContain(secret);
    expect(report).toContain("Recovery");
    expect(report).toContain("at Auth");
  });

  it("treats credential values as literals, preserving unrelated error context", () => {
    const password = "synthetic.[x]*(a)+?|$";
    const report = formatErrorReport({
      ...base,
      url: `${base.url}?password=${encodeURIComponent(password)}`,
      error: `Render failed; password=${password}; keep synthetic-other-context`,
    });

    expect(report).not.toContain(password);
    expect(report).not.toContain("[REDACTED]]");
    expect(report).toContain("password=[REDACTED]");
    expect(report).toContain("keep synthetic-other-context");
  });

  it("also masks a recognizable challenge in a diagnostic path", () => {
    const challenge = `rcv_${"d3".repeat(32)}`;
    const report = formatErrorReport({
      ...base,
      url: `https://beancount.io/auth/${challenge}`,
      error: "Render failed",
    });

    expect(report).not.toContain(challenge);
    expect(report).toContain("URL: https://beancount.io/auth/[REDACTED]");
  });

  it("redacts repeated sensitive parameters and a complete multiline value before truncating stacks", () => {
    const first = "first-synthetic-token";
    const second = "second-synthetic-token";
    const password = "synthetic-password\ncontinuation";
    const error = new Error(`Failure ${first}`);
    error.stack = Array.from({ length: 19 }, (_, i) => `    at f${i}`)
      .concat(`    at callback ${password}`, `    at callback ${second}`)
      .join("\n");
    const report = formatErrorReport({
      ...base,
      url: `https://beancount.io/auth/login?token=${first}&token=${second}&password=${encodeURIComponent(password)}`,
      error,
    });

    for (const secret of [first, second, ...password.split("\n")])
      expect(report).not.toContain(secret);
    expect(report).toContain("at f18");
    expect(report).toContain("…");
  });

  it.each([
    "not a URL?token=synthetic-invalid-url-secret",
    `https://beancount.io/auth/login?token=${"x".repeat(20_000)}`,
    "javascript:synthetic-unsafe-url-secret",
  ])("replaces an invalid, oversized or non-web diagnostic URL", (url) => {
    const report = formatErrorReport({ ...base, url, error: "Render failed" });

    expect(report).toContain("URL: [unavailable]");
    expect(report).not.toContain(url);
    expect(report).toContain("Error: Render failed");
  });
});
