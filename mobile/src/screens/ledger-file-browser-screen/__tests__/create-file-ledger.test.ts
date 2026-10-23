import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";

/**
 * w21/196: Create, then switch ledger before it finished: the success path
 * pushed the editor with only a path, and the editor reads its ledger from
 * the selection, so it opened (and could save) the other ledger's file.
 */
const source = fs
  .readFileSync(path.join(__dirname, "..", "index.tsx"), "utf8")
  .replace(/\s+/g, "");

describe("Create file after a ledger switch", () => {
  it("opens the editor only if still in the ledger and on the screen", () => {
    expect(
      source.includes("conststayedHere=ledgerVar()===ledgerId&&isHere();"),
    ).toBe(true);
    expect(
      source.includes(
        'voidinvalidateLedgerData(client,"file");if(!stayedHere)return;router.push({',
      ),
    ).toBe(true);
  });

  it("names the ledger the file was created in", () => {
    expect(
      source.includes(
        't("ledgerCreateFileSuccessIn",{name:filename,ledger:ledgerId,})',
      ),
    ).toBe(true);
    expect(en.ledgerCreateFileSuccessIn).toBe("Created {{name}} in {{ledger}}");
  });
});
