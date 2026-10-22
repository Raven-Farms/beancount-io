import fs from "fs";
import path from "path";
import { isShowingStaleDataFromQueries } from "../../../common/apollo/stale-data";

/**
 * w21/575: a failed pull on merchant detail replaced the rows Apollo still held
 * with "Failed to load" and no stale banner (w21/081 fixed Transactions and
 * account detail only). Source checks (the screen needs the native runtime),
 * with the rule the banner follows.
 */
const screen = fs
  .readFileSync(
    path.join(__dirname, "..", "merchant-detail-screen.tsx"),
    "utf8",
  )
  .replace(/\s+/g, "");

describe("a failed refresh on merchant detail", () => {
  it("is stale data when rows are held, and a failure when none are", () => {
    const failure = new Error("offline");
    expect(
      isShowingStaleDataFromQueries([{ data: { rows: [] }, error: failure }]),
    ).toBe(true);
    expect(
      isShowingStaleDataFromQueries([{ data: undefined, error: failure }]),
    ).toBe(false);
  });

  it("keeps the rows it holds and only fails an empty first load", () => {
    expect(
      screen.includes("constlistError=journalData?undefined:journalError;"),
    ).toBe(true);
    expect(screen.includes("sections={listError?[]:sections}")).toBe(true);
  });

  it("shows the shared stale banner over the list", () => {
    expect(
      screen.includes(
        "{isShowingStaleDataFromQueries([{data:journalData,error:journalError},])?(<StaleDataBanner/>):null}",
      ),
    ).toBe(true);
  });
});
