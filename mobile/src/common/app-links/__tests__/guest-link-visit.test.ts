import fs from "fs";
import path from "path";
import { guestLinkVisit } from "../guest-link-visit";
import { resolveAppLink } from "../resolve-app-link";

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
    ).toEqual({ ledgerId: "open_ledger/crypto-example", view: "transactions" });
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
