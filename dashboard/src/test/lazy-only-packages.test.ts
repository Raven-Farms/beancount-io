import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/** Every source file under `dir`, recursively. */
function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sources(path);
    return /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) ? [path] : [];
  });
}

const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&");

describe("packages that only a rare moment needs stay out of the page bundles", () => {
  it.each([
    // Importing it injects Stripe's script from js.stripe.com; only a payment
    // that needs the bank's approval should fetch it (w1/175).
    ["@stripe/stripe-js"],
    // Only a confirmed payment celebrates (w2/m54).
    ["canvas-confetti"],
  ])("%s is only ever imported dynamically or for types", (pkg) => {
    const files = sources(join(process.cwd(), "src"));
    const importers = files.filter((file) =>
      readFileSync(file, "utf8").includes(pkg),
    );
    const staticImport = new RegExp(
      `^import\\s+(?!type\\b)[^;]*from\\s+["']${escape(pkg)}["']`,
      "m",
    );
    const staticImports = importers.filter((file) =>
      staticImport.test(readFileSync(file, "utf8")),
    );

    expect(files.length).toBeGreaterThan(500);
    expect(importers.length).toBeGreaterThan(0);
    expect(staticImports).toEqual([]);
  });
});
