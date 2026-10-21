import { parseDirectiveDate } from "../directive-date";
import { BadUserInputError } from "@/shared/errors";

describe("parseDirectiveDate", () => {
  it.each([
    "2026-01-01",
    "2024-02-29",
    "2026-12-31",
    // w4/m38: early years keep their year, leap days included.
    "0001-01-01",
    "0004-02-29",
    "0099-12-31",
    "0100-01-01",
  ])("accepts %s", (value) => {
    const date = parseDirectiveDate(value);
    expect(date.toISOString().slice(0, 10)).toBe(value);
    expect(date.getUTCFullYear()).toBe(Number(value.slice(0, 4)));
  });

  it.each([
    "2026-13-45",
    "2026-02-30",
    "2025-02-29",
    "2026-00-10",
    "0000-01-01",
    "0099-02-29",
    "0100-02-29",
    "2026-1-5",
    "26-01-05",
    "2026/01/05",
    "2026-01-05T00:00:00Z",
    "yesterday",
    "",
  ])("refuses %j as the caller's input, naming it", (value) => {
    expect(() => parseDirectiveDate(value, "entry 3 date")).toThrow(
      BadUserInputError,
    );
    expect(() => parseDirectiveDate(value, "entry 3 date")).toThrow(
      /entry 3 date/,
    );
  });
});
