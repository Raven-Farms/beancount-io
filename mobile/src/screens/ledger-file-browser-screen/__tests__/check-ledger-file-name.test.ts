import fs from "fs";
import path from "path";
import { checkLedgerFileName, listingHasFile, parentDirectory } from "../utils";

// New Ledger File used to grey out Create with no reason, and refused folder
// paths the server accepts (w21/014). Each refusal now names its rule.
describe("checkLedgerFileName", () => {
  const existing = ["main.bean", "accounts.beancount"];

  it("says a name already exists, after adding .bean", () => {
    expect(checkLedgerFileName("main", existing)).toEqual({
      ok: false,
      issue: "exists",
      filename: "main.bean",
    });
  });

  it("refuses traversal, backslashes and empty folder names as a path issue", () => {
    for (const input of [
      "../qa.bean",
      "sub/../x.bean",
      "./x.bean",
      "/abs.bean",
      "sub//x.bean",
      "sub\\x.bean",
      "x\u0007.bean",
    ]) {
      expect(checkLedgerFileName(input, existing)).toEqual({
        ok: false,
        issue: "path",
      });
    }
  });

  it("refuses another extension or a bare extension", () => {
    expect(checkLedgerFileName("notes.txt", existing).ok).toBe(false);
    expect(checkLedgerFileName("notes.txt", existing)).toEqual({
      ok: false,
      issue: "extension",
    });
    expect(checkLedgerFileName(".bean", existing)).toEqual({
      ok: false,
      issue: "extension",
    });
  });

  it("accepts a new name and a relative folder path", () => {
    expect(checkLedgerFileName("notes", existing)).toEqual({
      ok: true,
      filename: "notes.bean",
    });
    expect(checkLedgerFileName(" sub/notes.beancount ", existing)).toEqual({
      ok: true,
      filename: "sub/notes.beancount",
    });
  });

  it("leaves an empty field silently disabled", () => {
    expect(checkLedgerFileName("   ", existing)).toEqual({
      ok: false,
      issue: "empty",
    });
  });
});

describe("New Ledger File dialog", () => {
  const read = (...parts: string[]) =>
    fs.readFileSync(path.join(__dirname, ...parts), "utf8");

  it("maps each refusal to its message", () => {
    const screen = read("..", "index.tsx");
    expect(
      screen.includes('t("ledgerFileNameExists", { name: check.filename })'),
    ).toBe(true);
    expect(screen.includes('t("ledgerFileNameExtension")')).toBe(true);
    expect(screen.includes('t("ledgerFileNamePath")')).toBe(true);
  });

  it("shows a string verdict under the field and disables Confirm on it", () => {
    const modal = read(
      "..",
      "..",
      "..",
      "components",
      "text-input-modal",
      "index.tsx",
    );
    expect(
      modal.includes("const isConfirmDisabled = validation !== true || busy;"),
    ).toBe(true);
    expect(
      modal.includes(
        'const inputError = typeof validation === "string" ? validation : null;',
      ),
    ).toBe(true);
  });
});

// w21/222: `sub/notes` passed at the root even when `sub/notes.bean` existed;
// the dialog closed and the create failed.
describe("a new file into a folder that already holds it", () => {
  it("is refused once the folder's listing says so", () => {
    const folder = [
      { path: "sub/notes.bean", type: "file" },
      { path: "sub/inner", type: "dir" },
    ];
    expect(listingHasFile(folder, "sub/notes.bean")).toBe(true);
    expect(listingHasFile(folder, "/sub/notes.bean")).toBe(true);
    expect(listingHasFile(folder, "sub/other.bean")).toBe(false);
    // A folder of that name is not the file.
    expect(listingHasFile(folder, "sub/inner")).toBe(false);
    expect(listingHasFile([], "sub/notes.bean")).toBe(false);
  });

  it("names the clash in the dialog by treating the found file as existing", () => {
    // The bare current-folder names do not see it...
    expect(checkLedgerFileName("sub/notes", ["main.bean", "sub"]).ok).toBe(
      true,
    );
    // ...and once the listing found it, the same input is refused with its name.
    expect(
      checkLedgerFileName("sub/notes", ["main.bean", "sub", "sub/notes.bean"]),
    ).toEqual({ ok: false, issue: "exists", filename: "sub/notes.bean" });
  });

  it("finds the folder to look in", () => {
    expect(parentDirectory("sub/notes.bean")).toBe("sub");
    expect(parentDirectory("a/b/c.bean")).toBe("a/b");
    expect(parentDirectory("main.bean")).toBe("");
  });

  it("checks that folder before the dialog closes", () => {
    const source = fs
      .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
      .replace(/\s+/g, "");
    const lookup = source.indexOf("query:GetLedgerDirContentDocument");
    const closes = source.indexOf("setCreateModalVisible(false);try{");
    expect(lookup > -1 && lookup < closes).toBe(true);
  });
});
