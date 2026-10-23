import { describe, expect, it } from "vitest";
import { majorUnits } from "../use-money-format";

describe("majorUnits", () => {
  it.each([
    ["a two-decimal currency", 14388, "usd", 143.88],
    ["an upper-case code", 14388, "USD", 143.88],
    ["a zero-decimal currency", 1500, "jpy", 1500],
    ["a three-decimal currency", 1500, "kwd", 1.5],
  ])("reads %s in its own minor unit", (_label, amount, currency, major) => {
    expect(majorUnits(amount, currency)).toBe(major);
  });
});
