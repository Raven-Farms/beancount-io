import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";

// w21/120: saving an emptied editor replaced the entry with a blank line — a
// delete without Delete's confirmation — and toasted "Transaction saved".
describe("saving an emptied Edit Transaction", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "..", "edit-transaction-screen.tsx"),
    "utf8",
  );

  it("writes nothing and points to Delete", () => {
    const guard = source.indexOf("if (!content.trim()) {");
    expect(guard > 0).toBe(true);
    // Checked before any write is attempted.
    expect(guard < source.indexOf("newContent: content")).toBe(true);
    expect(source.includes('setSaveError(t("editTransactionEmpty"));')).toBe(
      true,
    );
    expect(en.editTransactionEmpty.includes("Delete")).toBe(true);
  });
});
