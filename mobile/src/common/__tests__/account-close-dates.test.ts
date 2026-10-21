import { closeDatesOf, isOpenOn, openOn } from "../account-close-dates";

// w21/045: the posting picker offered a closed account, and the save was then
// refused at Done ("Posting to inactive account … (closed on …)").
describe("accounts open on an entry's date", () => {
  const closeDates = closeDatesOf([
    { account: "Assets:Checking", closedAt: null },
    { account: "Assets:Qa20261020Closed", closedAt: "2026-09-01" },
  ]);
  const accounts = [
    "Assets:Checking",
    "Assets:Qa20261020Closed",
    "Assets:Cash",
  ];

  it("leaves out an account closed before the entry's date", () => {
    expect(openOn(accounts, "2026-10-20", closeDates)).toEqual([
      "Assets:Checking",
      "Assets:Cash",
    ]);
  });

  it("offers it again for an entry back-dated to while it was open", () => {
    expect(openOn(accounts, "2026-08-15", closeDates)).toEqual(accounts);
  });

  it("keeps it on the close date itself, where Beancount books the posting first", () => {
    expect(isOpenOn("Assets:Qa20261020Closed", "2026-09-01", closeDates)).toBe(
      true,
    );
    expect(isOpenOn("Assets:Qa20261020Closed", "2026-09-02", closeDates)).toBe(
      false,
    );
  });

  it("offers everything until close dates load", () => {
    expect(openOn(accounts, "2026-10-20", closeDatesOf(undefined))).toEqual(
      accounts,
    );
  });
});

describe("the account picker", () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const source: string = require("fs").readFileSync(
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require("path").join(
      __dirname,
      "..",
      "..",
      "screens",
      "account-picker-screen",
      "account-picker-screen.tsx",
    ),
    "utf8",
  );

  it("filters posting pickers by the entry date and leaves the filter picker whole", () => {
    expect(
      source.includes(
        "openOn(opened, entryDate ?? getFormatDate(new Date()), closeDates)",
      ),
    ).toBe(true);
    expect(
      source.includes('type === "filter"\n      ? withParentAccounts(opened)'),
    ).toBe(true);
  });
});

// w21/122: a closed account's exact name offered Create in the picker, and
// Open Account then refused it as "already open".
describe("closedAccountNamed", () => {
  const { closedAccountNamed } = require("../account-close-dates");
  const closeDates = new Map([["Liabilities:QaOldCard", "2026-09-01"]]);

  it("finds a closed account by its exact name, ignoring case", () => {
    expect(
      closedAccountNamed("liabilities:qaoldcard ", "2026-10-21", closeDates),
    ).toEqual({ account: "Liabilities:QaOldCard", closedAt: "2026-09-01" });
  });

  it("finds nothing for a partial name or before the close", () => {
    expect(
      closedAccountNamed("Liabilities:QaOld", "2026-10-21", closeDates),
    ).toBe(null);
    expect(
      closedAccountNamed("Liabilities:QaOldCard", "2026-08-01", closeDates),
    ).toBe(null);
  });

  it("replaces Create in the picker and 'already open' in Open Account", () => {
    const read = (...parts: string[]) =>
      require("fs").readFileSync(
        require("path").join(__dirname, "..", "..", ...parts),
        "utf8",
      ) as string;
    const picker = read(
      "screens",
      "account-picker-screen",
      "account-picker-screen.tsx",
    );
    expect(picker.includes("!closedMatch &&")).toBe(true);
    expect(picker.includes('t("accountPickerClosedOn", {')).toBe(true);
    const open = read(
      "screens",
      "open-account-screen",
      "open-account-screen.tsx",
    );
    expect(open.includes('? t("openAccountClosed", {')).toBe(true);
  });
});
