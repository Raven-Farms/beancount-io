import fs from "fs";
import path from "path";
import {
  clearGuestVisit,
  guestVisitVar,
  startGuestVisit,
  updateGuestVisit,
} from "../../../common/guest/guest-state";

// w21/525: a journal link's filters stayed on the guest visit, so they followed
// the guest to every other example and came back after Reset.
const read = (file: string) =>
  fs.readFileSync(path.join(__dirname, "..", file), "utf8").replace(/\s+/g, "");

describe("a guest journal link's filters", () => {
  afterEach(() => clearGuestVisit());

  it("are gone from the visit once an update clears them", () => {
    startGuestVisit("https://beancount.io");
    updateGuestVisit({
      ledgerId: "open_ledger/example",
      view: "transactions",
      filters: { account: "Expenses:Food:Restaurant" } as never,
    });
    expect(guestVisitVar()?.filters !== undefined).toBe(true);
    updateGuestVisit({ filters: undefined });
    expect(guestVisitVar()?.filters).toBe(undefined);
    updateGuestVisit({ ledgerId: "open_ledger/nvidia" });
    expect(guestVisitVar()?.filters).toBe(undefined);
  });

  it("are spent when the example seeds them, and cleared on switching", () => {
    const provider = read("example-ledger-provider.tsx");
    expect(
      provider.includes(
        "transactionFilters({ledgerId,filters:linkFilters});updateGuestVisit({filters:undefined});",
      ),
    ).toBe(true);
    expect(
      read("examples-layout.tsx").includes(
        "updateGuestVisit({ledgerId,resumeFailure:undefined,filters:undefined,});",
      ),
    ).toBe(true);
  });
});
