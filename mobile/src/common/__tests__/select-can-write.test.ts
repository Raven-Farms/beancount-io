import fs from "fs";
import path from "path";
import { selectCanWrite } from "../ledger-access";

/**
 * w21/151: a refetch that failed offline kept its data but set `error`, and
 * any error read as "no write permission", so returning to the app offline
 * turned a dirty editor read-only.
 */
const writable = {
  getLedger: { id: "alice/books", permissions: { push: true, admin: false } },
};
const read = (error: unknown) =>
  selectCanWrite({
    guest: false,
    ledgerId: "alice/books",
    data: writable,
    error,
  });
const graphQL = (code: string) => ({
  graphQLErrors: [{ extensions: { code } }],
});

describe("selectCanWrite", () => {
  it("keeps cached write access through a failed refetch", () => {
    expect(read(undefined)).toBe(true);
    expect(read(new Error("Network request failed"))).toBe(true);
    expect(read(graphQL("INTERNAL_SERVER_ERROR"))).toBe(true);
  });

  it("reads as read-only once access is answered gone", () => {
    expect(read(graphQL("FORBIDDEN"))).toBe(false);
    expect(read(graphQL("NOT_FOUND"))).toBe(false);
    expect(read(graphQL("UNAUTHENTICATED"))).toBe(false);
  });

  it("still refuses guests, other ledgers and read-only grants", () => {
    expect(
      selectCanWrite({
        guest: true,
        ledgerId: "alice/books",
        data: writable,
        error: undefined,
      }),
    ).toBe(false);
    expect(
      selectCanWrite({
        guest: false,
        ledgerId: "bob/other",
        data: writable,
        error: undefined,
      }),
    ).toBe(false);
    expect(
      selectCanWrite({
        guest: false,
        ledgerId: "alice/books",
        data: {
          getLedger: {
            id: "alice/books",
            permissions: { push: false, admin: false },
          },
        },
        error: undefined,
      }),
    ).toBe(false);
    expect(
      selectCanWrite({
        guest: false,
        ledgerId: "alice/books",
        data: undefined,
        error: undefined,
      }),
    ).toBe(false);
  });

  it("is what useLedgerAccess answers with", () => {
    const hook = fs.readFileSync(
      path.join(__dirname, "..", "hooks", "use-ledger-access.ts"),
      "utf8",
    );
    expect(
      hook.includes(
        "canWrite: selectCanWrite({ guest: !!guest, ledgerId, data, error }),",
      ),
    ).toBe(true);
  });
});
