import {
  asciiHost,
  isOfficialServerUrl,
  validateServerUrl,
} from "../server-url-validation";

// w21/216: these passed validation as a separate override that could never
// match the backend's issuer, and failed as "incompatible".
describe("server URL normalization", () => {
  const ok = (input: string): string => {
    const result = validateServerUrl(input, { allowInsecureLocalhost: false });
    return result.ok ? result.url : `rejected:${result.code}`;
  };

  it("drops an empty query or fragment, so the default stays the default", () => {
    expect(ok("https://beancount.io/?")).toBe("https://beancount.io/");
    expect(ok("https://beancount.io/#")).toBe("https://beancount.io/");
    expect(ok("https://beancount.io/?#")).toBe("https://beancount.io/");
    expect(isOfficialServerUrl("https://beancount.io/?")).toBe(true);
    expect(ok("https://host.example/beancount#")).toBe(
      "https://host.example/beancount/",
    );
  });

  it("still rejects a query or fragment that says something", () => {
    expect(ok("https://host.example/?a=1")).toBe("rejected:query");
    expect(ok("https://host.example/#top")).toBe("rejected:query");
  });

  it("drops a trailing dot, which names the same host", () => {
    expect(ok("https://host.example./")).toBe("https://host.example/");
    expect(ok("https://host.example.:8443/x")).toBe(
      "https://host.example:8443/x/",
    );
  });

  it("writes a Unicode host the way the backend's issuer does", () => {
    // The reference forms are what the platform's own IDNA conversion gives.
    const expected: Record<string, string> = {
      "bücher.example": "xn--bcher-kva.example",
      "BÜCHER.example": "xn--bcher-kva.example",
      "münchen.de": "xn--mnchen-3ya.de",
      "日本語.jp": "xn--wgv71a119e.jp",
      "почта.рф": "xn--80a1acny.xn--p1ai",
      "ドメイン名例.jp": "xn--eckwd4c7cu47r2wf.jp",
      "a-ü.example": "xn--a--yka.example",
      "😀.example": "xn--e28h.example",
    };
    for (const [unicode, ascii] of Object.entries(expected)) {
      expect(asciiHost(unicode)).toBe(ascii);
    }
  });

  it("leaves an ASCII host, an IP and a port alone", () => {
    expect(ok("https://Host.Example/")).toBe("https://host.example/");
    expect(ok("https://203.0.113.7:8443/")).toBe("https://203.0.113.7:8443/");
    expect(asciiHost("localhost")).toBe("localhost");
  });
});
