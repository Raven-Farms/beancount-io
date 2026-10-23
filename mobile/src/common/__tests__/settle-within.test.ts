import fs from "fs";
import path from "path";
import { settleWithin } from "../settle-within";

// w21/183: the splash waited out the OS's ~60 s request timeout on a lossy
// network, with the cache ready.
describe("settleWithin", () => {
  it("returns a result that arrives in time", async () => {
    expect(JSON.stringify(await settleWithin(Promise.resolve(7), 50))).toBe(
      JSON.stringify({ status: "done", value: 7 }),
    );
  });

  it("gives up on one that does not, leaving it running", async () => {
    let settled = false;
    const slow = new Promise<number>((resolve) =>
      setTimeout(() => {
        settled = true;
        resolve(1);
      }, 40),
    );
    expect((await settleWithin(slow, 5)).status).toBe("timeout");
    expect(settled).toBe(false);
    await slow;
    expect(settled).toBe(true);
  });

  it("passes a rejection inside the window through", async () => {
    let caught = "";
    try {
      await settleWithin(Promise.reject(new Error("gone")), 50);
    } catch (error) {
      caught = (error as Error).message;
    }
    expect(caught).toBe("gone");
  });

  it("bounds the splash's ledger check and keeps watching it", () => {
    const splash = fs.readFileSync(
      path.join(
        __dirname,
        "..",
        "providers",
        "splash-provider",
        "splash-provider.tsx",
      ),
      "utf8",
    );
    expect(
      splash.includes("settleWithin(check, LEDGER_CHECK_DEADLINE_MS)"),
    ).toBe(true);
    expect(splash.includes("check.catch((late: unknown) => {")).toBe(true);
  });

  // w21/362: a late NOT_FOUND for the launch ledger cleared whatever the user
  // had picked since.
  it("a late check clears only the ledger it validated", () => {
    const splash = fs
      .readFileSync(
        path.join(
          __dirname,
          "..",
          "providers",
          "splash-provider",
          "splash-provider.tsx",
        ),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(
      splash.includes(
        "if(ledgerVar()===ledger&&shouldClearLedgerSelection(late)){ledgerVar(null);}",
      ),
    ).toBe(true);
  });
});
