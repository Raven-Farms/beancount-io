import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * Importing `@stripe/stripe-js` injects Stripe's script from js.stripe.com, so
 * one static import would make every page that bundles it fetch Stripe.js.
 * Only a payment that needs the bank's approval should (w1/175).
 */

/** Every source file under `dir`, recursively. */
function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) ? [path] : [];
  });
}

describe("Stripe.js stays out of the page bundles", () => {
  it("is only ever imported dynamically or for types", () => {
    const files = sources(join(process.cwd(), "src"));
    const importers = files.filter((file) =>
      readFileSync(file, "utf8").includes("@stripe/stripe-js"),
    );
    const staticImports = importers.filter((file) =>
      /^import\s+(?!type\b)[^;]*from\s+["']@stripe\/stripe-js["']/m.test(
        readFileSync(file, "utf8"),
      ),
    );

    expect(files.length).toBeGreaterThan(500);
    expect(importers.length).toBeGreaterThan(0);
    expect(staticImports).toEqual([]);
  });
});
