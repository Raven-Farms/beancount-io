import { translationLocales } from "./locale-parity";

// w21/582: in Ukrainian and Russian the file editor's "Discard" button read
// "Скасувати" / "Отменить", the same word as Cancel beside it, so a tap meant to
// keep the edits could throw them away.
describe("an alert's destructive button", () => {
  it("never reads the same as the Cancel beside it, in any language", () => {
    for (const locale of translationLocales()) {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const catalog = require(`../${locale}`)[locale];
      const norm = (text: string) =>
        text.trim().toLocaleLowerCase(locale).replace(/[.…]/g, "");
      expect(norm(catalog.ledgerEditorDiscardChanges)).not.toBe(
        norm(catalog.cancel),
      );
    }
  });

  it("says discard in Ukrainian and Russian", () => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    expect(require("../uk").uk.ledgerEditorDiscardChanges).toBe("Відкинути");
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    expect(require("../ru").ru.ledgerEditorDiscardChanges).toBe("Отбросить");
  });
});
