import fs from "fs";
import path from "path";
import { DIFF_PAGE_LINES, nextDiffChunk, parseDiff } from "../diff-utils";

// w21/379: the diff was drawn in full inside the screen's own scroll, so a
// commit adding 20,000 lines built 20,000 rows before it answered a touch.
describe("a large commit's diff", () => {
  it("is revealed a page at a time", () => {
    expect(DIFF_PAGE_LINES).toBe(500);
    expect(nextDiffChunk(500, 20_006)).toBe(500);
    expect(nextDiffChunk(20_000, 20_006)).toBe(6);
    expect(nextDiffChunk(20_006, 20_006)).toBe(0);
    expect(nextDiffChunk(600, 500)).toBe(0);
  });

  it("parses 20,000 added lines quickly", () => {
    const body = Array.from({ length: 20_000 }, (_, i) => `+line ${i}`).join(
      "\n",
    );
    const started = Date.now();
    const lines = parseDiff(`@@ -0,0 +1,20000 @@\n${body}\n`);
    expect(lines.length >= 20_000).toBe(true);
    expect(Date.now() - started < 2000).toBe(true);
  });

  it("draws only the lines shown, with a button for the rest", () => {
    const src = fs
      .readFileSync(path.join(__dirname, "../commit-detail-screen.tsx"), "utf8")
      .replace(/\s+/g, "");
    expect(src.includes("data={diffLines.slice(0,shown)}")).toBe(true);
    expect(
      src.includes("useMemo(()=>(diff?parseDiff(diff):null),[diff])"),
    ).toBe(true);
    expect(src.includes("setShown((count)=>count+DIFF_PAGE_LINES)")).toBe(true);
    expect(src.includes("{shown<diffLines.length?")).toBe(true);
  });
});
