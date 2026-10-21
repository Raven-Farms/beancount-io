import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";
import { ru } from "../../../translations/ru";
import { fa } from "../../../translations/fa";

// w21/091: each error row read "line N" in English in every language.
describe("the file editor's error row location", () => {
  it("is a translated key", () => {
    expect(en.ledgerEditorErrorLine).toBe("line {{line}}");
    expect(ru.ledgerEditorErrorLine).toBe("строка {{line}}");
    expect(fa.ledgerEditorErrorLine).toBe("خط {{line}}");
  });

  it("is what the row renders", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "index.tsx"),
      "utf8",
    );
    expect(
      source.includes('t("ledgerEditorErrorLine", { line: err.lineno })'),
    ).toBe(true);
    expect(source.includes("`line ${err.lineno}`")).toBe(false);
  });
});
