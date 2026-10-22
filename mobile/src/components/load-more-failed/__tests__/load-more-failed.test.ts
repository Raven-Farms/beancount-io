import fs from "fs";
import path from "path";

/**
 * w21/353: a failed next page only logged, so the list ended as if it were the
 * whole history. Source checks, since the screens need the native runtime.
 */
const read = (relative: string) =>
  fs
    .readFileSync(path.join(__dirname, "../../..", relative), "utf8")
    .replace(/\s+/g, "");

describe("a paged list whose next page failed", () => {
  for (const file of [
    "screens/transactions-screen/transactions-screen.tsx",
    "screens/account-detail-screen/account-detail-screen.tsx",
  ]) {
    it(`${file.split("/")[1]} shows a footer with Retry`, () => {
      const src = read(file);
      // The failure is remembered per list, and set when the page fails.
      expect(src.includes("loadMoreFailedFor===listKey")).toBe(true);
      expect(src.includes("setLoadMoreFailedFor(")).toBe(true);
      // Reaching the end does not ask again while failed; Retry does.
      expect(src.includes("if(loadMoreFailed&&!retry)return;")).toBe(true);
      expect(src.includes("onEndReached={()=>voidloadMore()}")).toBe(true);
      expect(
        src.includes(
          "loadMoreFailed&&hasMore?(<LoadMoreFailedonRetry={()=>voidloadMore(true)}/>)",
        ),
      ).toBe(true);
    });
  }

  it("has its message in every language", () => {
    const dir = path.join(__dirname, "../../../translations");
    const missing = fs
      .readdirSync(dir)
      .filter((name) => /^[a-z]{2}\.ts$/.test(name))
      .filter(
        (name) =>
          !fs
            .readFileSync(path.join(dir, name), "utf8")
            .includes("loadMoreFailed:"),
      );
    expect(missing).toEqual([]);
  });
});
