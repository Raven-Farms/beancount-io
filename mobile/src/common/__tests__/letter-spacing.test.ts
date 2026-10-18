/**
 * Every `letterSpacing` in the app goes through `letterSpacing()` from
 * `rtl.ts`, which drops it in a right-to-left layout. A literal one splits
 * Persian letters apart — the Payee caption پیشنهادها rendered as
 * "پیشنهاد ها" (w0/049). Zero is the only literal allowed: it tracks nothing.
 */
const fs = require("fs") as typeof import("fs");
const path = require("path") as typeof import("path");

const SRC = path.join(__dirname, "..", "..");

function sources(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      return entry.name === "__tests__" || entry.name === "generated-graphql"
        ? []
        : sources(full);
    }
    return /\.tsx?$/.test(entry.name) ? [full] : [];
  });
}

/** `letterSpacing:` values that are neither `letterSpacing(…)` nor 0. */
function bypasses(source: string): string[] {
  return Array.from(source.matchAll(/letterSpacing:\s*([^,}\n]+)/g))
    .map((match) => match[1].trim())
    .filter((value) => !/^letterSpacing\(/.test(value) && value !== "0");
}

describe("letter spacing", () => {
  it("goes through the right-to-left-safe helper everywhere", () => {
    const offenders = sources(SRC).flatMap((file) =>
      bypasses(fs.readFileSync(file, "utf8")).map(
        (value) => `${path.relative(SRC, file)}: letterSpacing: ${value}`,
      ),
    );
    expect(offenders).toEqual([]);
  });

  it("flags a literal and accepts the helper or zero", () => {
    expect(bypasses("letterSpacing: 0.8,")).toEqual(["0.8"]);
    expect(bypasses("letterSpacing: -1 }")).toEqual(["-1"]);
    expect(bypasses("letterSpacing: letterSpacing(0.8),")).toEqual([]);
    expect(bypasses("letterSpacing: 0,")).toEqual([]);
  });
});
