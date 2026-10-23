import { readFileSync } from "fs";
import { join } from "path";
import { describe, expect, it } from "vitest";

const root = join(__dirname, "../../../..");

/** Every event `AnalyticsEvents` declares, read from the source. */
function declaredEvents(): string[] {
  const source = readFileSync(
    join(root, "src/common/analytics/events.ts"),
    "utf-8",
  );
  const start = source.indexOf("export interface AnalyticsEvents {");
  const body = source.slice(start, source.indexOf("\n}\n", start));
  return [...body.matchAll(/^ {2}([a-z][a-z_]*): /gm)].map((m) => m[1]);
}

describe("event taxonomy", () => {
  it("documents every event the dashboard can track (w1/179)", () => {
    const events = declaredEvents();
    // Anti-vacuity: the map holds more than a dozen events today.
    expect(events.length).toBeGreaterThanOrEqual(15);
    const doc = readFileSync(join(root, "docs/event-taxonomy.md"), "utf-8");
    const missing = events.filter((event) => !doc.includes(`| \`${event}\` |`));
    expect(missing).toEqual([]);
  });
});
