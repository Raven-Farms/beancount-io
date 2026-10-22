import fs from "fs";
import path from "path";
import { guestLinkVisit } from "../guest-link-visit";
import { resolveAppLink } from "../resolve-app-link";
import { NO_FILTERS } from "../../../screens/transactions-screen/filters/types";

const HOSTED = "https://beancount.io/";
const link = (suffix: string) =>
  resolveAppLink(`https://beancount.io/ledger/${suffix}`)!;

describe("a signed-out link to a public example (w21/345)", () => {
  it("opens the README demo link's Reports as a guest", () => {
    const target = link("open_ledger/example/income-statement?time=2025");
    expect(guestLinkVisit(target, HOSTED)).toEqual({
      ledgerId: "open_ledger/example",
      view: "reports",
    });
  });

  it("maps home and journal links and every curated example", () => {
    expect(guestLinkVisit(link("open_ledger/nvidia"), HOSTED)).toEqual({
      ledgerId: "open_ledger/nvidia",
      view: "home",
    });
    expect(
      guestLinkVisit(link("open_ledger/crypto-example/journal"), HOSTED),
    ).toEqual({
      ledgerId: "open_ledger/crypto-example",
      view: "transactions",
      filters: NO_FILTERS,
    });
  });

  it("leaves other ledgers, other pages and other servers to sign-in", () => {
    expect(guestLinkVisit(link("alice/books/journal"), HOSTED)).toBe(null);
    // Pages the guest tabs do not have.
    expect(guestLinkVisit(link("open_ledger/example/budget"), HOSTED)).toBe(
      null,
    );
    expect(
      guestLinkVisit(link("open_ledger/example/account/Assets:Cash"), HOSTED),
    ).toBe(null);
    // Guests exist only on the official server.
    expect(
      guestLinkVisit(
        link("open_ledger/example/journal"),
        "https://books.example.test/",
      ),
    ).toBe(null);
  });

  it("the link handler starts the visit, drops the stash and navigates", () => {
    const src = fs
      .readFileSync(path.join(__dirname, "../use-app-link-handler.ts"), "utf8")
      .replace(/\s+/g, "");
    expect(
      src.includes(
        "guestLinkVisit(target,serverUrl);if(!guest)return;clearPendingAppLink();startGuestVisit(serverUrl);updateGuestVisit(guest);awaitafterNavigatorReady();",
      ),
    ).toBe(true);
    expect(src.includes("router.replace(exampleRoutes[guest.view])")).toBe(
      true,
    );
  });
});

// w21/489: the guest path never received a journal link's filters.
describe("a signed-out journal link with filters", () => {
  it("opens the example's Transactions with the account the link names", () => {
    const visit = guestLinkVisit(
      link("open_ledger/example/journal?account=Expenses:Food"),
      HOSTED,
    );
    expect(visit?.ledgerId).toBe("open_ledger/example");
    expect(visit?.view).toBe("transactions");
    expect(visit?.filters?.account).toBe("Expenses:Food");
  });

  it("carries a time window as the custom range", () => {
    const visit = guestLinkVisit(
      link("open_ledger/example/journal?time=2025-03"),
      HOSTED,
    );
    expect(visit?.filters?.range).toBe("custom");
    expect(visit?.filters?.startDate).toBe("2025-03-01");
    expect(visit?.filters?.endDate).toBe("2025-03-31");
  });

  it("carries none for the tabs that have no filters", () => {
    const visit = guestLinkVisit(link("open_ledger/example"), HOSTED);
    expect(visit !== null && "filters" in visit).toBe(false);
  });

  it("is kept on the visit and seeds the guest session's filters", () => {
    const read = (file: string) =>
      fs
        .readFileSync(path.join(__dirname, "../../..", file), "utf8")
        .replace(/\s+/g, "");
    expect(
      read("common/guest/guest-state.ts").includes(
        'Pick<GuestVisit,"ledgerId"|"view"|"resumeFailure"|"filters">',
      ),
    ).toBe(true);
    const provider = read("screens/examples/example-ledger-provider.tsx");
    expect(
      provider.includes(
        "linkFilters?{ledgerId,filters:linkFilters}:NO_SCOPED_FILTERS",
      ),
    ).toBe(true);
    expect(
      provider.includes(
        "if(!linkFilters)return;transactionFilters({ledgerId,filters:linkFilters});",
      ),
    ).toBe(true);
  });
});

// w21/490: Accounts and Files are guest tabs, and their links waited behind sign-in.
describe("a signed-out link to an example's Accounts or Files tab", () => {
  it("opens the Accounts tab", () => {
    expect(
      guestLinkVisit(link("open_ledger/example/accounts"), HOSTED),
    ).toEqual({ ledgerId: "open_ledger/example", view: "accounts" });
  });

  it("opens the Files tab for the tree of the main branch", () => {
    expect(
      guestLinkVisit(link("open_ledger/example/files/tree/main"), HOSTED),
    ).toEqual({ ledgerId: "open_ledger/example", view: "files" });
  });

  it("still leaves the open-account form and a file to sign-in, and another branch is no link", () => {
    expect(
      guestLinkVisit(
        link("open_ledger/example/accounts?action=open-account"),
        HOSTED,
      ),
    ).toBe(null);
    expect(
      guestLinkVisit(
        link("open_ledger/example/files/blob/main/main.bean"),
        HOSTED,
      ),
    ).toBe(null);
    // Another branch is no app link at all.
    expect(
      resolveAppLink(
        "https://beancount.io/ledger/open_ledger/example/files/tree/dev",
      ),
    ).toBe(null);
  });
});
