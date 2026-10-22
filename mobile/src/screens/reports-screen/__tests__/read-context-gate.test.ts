import fs from "fs";
import path from "path";
import { selectReadContextState } from "../../../common/apollo/card-load-state";

/**
 * w21/406: Reports and account detail drew in a blind "USD" with the English
 * root names until the read context landed, and for good if it failed. Source
 * checks: the screens need the native runtime.
 */
const read = (relative: string) =>
  fs
    .readFileSync(path.join(__dirname, "../../..", relative), "utf8")
    .replace(/\s+/g, "");

describe("the read context gate", () => {
  it("is loading until the context arrives, ready with it, failed with an error and none", () => {
    expect(selectReadContextState(undefined, undefined)).toBe("loading");
    expect(selectReadContextState({ getLedger: {} }, undefined)).toBe("ready");
    expect(selectReadContextState(undefined, new Error("offline"))).toBe(
      "failed",
    );
  });

  it("Reports holds its cards for the context, and fails with it", () => {
    const src = read("screens/reports-screen/reports-screen.tsx");
    expect(
      src.includes(
        'constisLoading=statementState==="loading"||contextState==="loading";',
      ),
    ).toBe(true);
    expect(
      src.includes(
        'constfailed=statementState==="failed"||contextState==="failed";',
      ),
    ).toBe(true);
    expect(
      src.includes("Promise.all([incomeRefetch(),ledgerMetaRefetch()])"),
    ).toBe(true);
  });

  it("Reports leaves Recent transactions out on a failure, so it cannot say 'No transactions yet'", () => {
    const src = read("screens/reports-screen/reports-screen.tsx");
    expect(src.includes("{failed?null:(<AccountTransactionsCard")).toBe(true);
    expect(src.includes("statementLoading={isLoading}")).toBe(true);
  });

  it("account detail holds the chart and list for the context, and fails with it", () => {
    const src = read("screens/account-detail-screen/account-detail-screen.tsx");
    expect(
      src.includes("selectReadContextState(ledgerReadData,ledgerReadError)"),
    ).toBe(true);
    expect(src.includes('||contextState==="loading";')).toBe(true);
    expect(
      src.includes("sections={isInitialLoading||contextFailed?[]:sections}"),
    ).toBe(true);
    expect(src.includes("voidledgerMetaRefetch().catch(()=>undefined);")).toBe(
      true,
    );
  });
});
