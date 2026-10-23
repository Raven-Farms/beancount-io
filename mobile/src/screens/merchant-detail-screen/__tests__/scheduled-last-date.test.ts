import fs from "fs";
import path from "path";

// w21/335: the merchant detail header's date range ended on a pre-entered
// payment as if it had been made, and the recurrence hook counted pre-entered
// events as history. The screens use hooks this runner cannot execute, so the
// wiring is checked on source.
describe("pre-entered payments on the merchant screens", () => {
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", "..", ...parts), "utf8")
      .replace(/\s+/gu, "");

  it("labels a last date after today as scheduled", () => {
    const detail = read("merchant-detail-screen", "merchant-detail-screen.tsx");
    expect(detail.includes("consttoday=useToday();")).toBe(true);
    expect(
      detail.includes(
        "merchantDateRangeText(stats.firstDate,stats.lastDate,today,locale,t,)",
      ),
    ).toBe(true);
  });

  it("measures enough history up to today", () => {
    const hook = read("merchants-screen", "use-payee-recurrence.ts");
    expect(hook.includes("hasEnoughHistory(series,today)")).toBe(true);
  });
});
