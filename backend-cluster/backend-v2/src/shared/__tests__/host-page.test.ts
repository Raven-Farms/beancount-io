import { BadUserInputError } from "@/shared/errors";
import { assertHostPage, HOST_PAGE_MAX } from "@/shared/host-page";

describe("assertHostPage", () => {
  it.each([
    [undefined, undefined],
    [1, 1],
    [7, HOST_PAGE_MAX],
  ])("accepts page %p and limit %p", (page, limit) => {
    expect(() => assertHostPage(page, limit)).not.toThrow();
  });

  // w23/038: the host answers these with its own defaults, so 51 came back
  // as 50 and read as the last page.
  it.each([
    [1, HOST_PAGE_MAX + 1, "limit must be at most 50"],
    [1, 1000, "limit must be at most 50"],
    [0, 10, "page must be a positive integer"],
    [1, -1, "limit must be a positive integer"],
    [1, 2.5, "limit must be a positive integer"],
  ])("refuses page %p and limit %p", (page, limit, message) => {
    expect(() => assertHostPage(page, limit)).toThrow(BadUserInputError);
    expect(() => assertHostPage(page, limit)).toThrow(message);
  });
});
