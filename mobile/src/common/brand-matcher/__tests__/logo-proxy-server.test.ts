import fs from "fs";
import path from "path";
import { logoProxyForServer } from "..";

/**
 * w21/155: on a server the user chose themselves, the app still asked the
 * hosted logo service for every brand-matched payee.
 */
const proxy = "https://logos.example.test/api/logo";

describe("logoProxyForServer", () => {
  it("uses the configured proxy on the build's own server", () => {
    expect(
      logoProxyForServer(
        "https://beancount.io/",
        "https://beancount.io/",
        proxy,
      ),
    ).toBe(proxy);
    expect(
      logoProxyForServer(
        "https://Beancount.io",
        "https://beancount.io/",
        proxy,
      ),
    ).toBe(proxy);
  });

  it("falls back to glyphs on any other server", () => {
    expect(
      logoProxyForServer(
        "https://books.example.test/",
        "https://beancount.io/",
        proxy,
      ),
    ).toBe("");
  });

  it("is what the row icon builds its logo URL from", () => {
    const icon = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "..",
        "..",
        "components",
        "account-type-icon",
        "index.tsx",
      ),
      "utf8",
    );
    expect(icon.includes("buildLogoUrl(domain, logoProxyUrl)")).toBe(true);
    expect(icon.includes("buildLogoUrl(domain, config.logoProxyUrl)")).toBe(
      false,
    );
  });
});
