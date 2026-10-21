import {
  decodeLedgerFileContent,
  encodeLedgerFileContent,
  isLosslessLedgerFileContent,
  lineEndingOf,
  withLineEnding,
  isOverEditLimit,
  isUnreadableLargeFile,
} from "../ledger-file-content";

// w21/042: a Latin-1 "Café" decoded to "Caf�" and one unrelated save
// wrote EF BF BD over the é.
const b64 = (bytes: number[]) => Buffer.from(bytes).toString("base64");

describe("isLosslessLedgerFileContent", () => {
  it("refuses a Latin-1 byte, which UTF-8 decoding replaces", () => {
    const latin1 = b64([0x43, 0x61, 0x66, 0xe9, 0x0a]); // "Caf\xE9\n"
    expect(isLosslessLedgerFileContent(latin1, "base64")).toBe(false);
    // What saving it would have written.
    expect(
      Buffer.from(
        encodeLedgerFileContent(decodeLedgerFileContent(latin1, "base64")),
        "base64",
      ).toString("hex"),
    ).toBe("436166efbfbd0a");
  });

  it("accepts UTF-8 multibyte text and round-trips it byte for byte", () => {
    const text = '2026-01-01 * "Café ☕ 日本"\n';
    const encoded = Buffer.from(text, "utf8").toString("base64");
    expect(isLosslessLedgerFileContent(encoded, "base64")).toBe(true);
    expect(
      encodeLedgerFileContent(decodeLedgerFileContent(encoded, "base64")),
    ).toBe(encoded);
  });

  it("keeps a UTF-8 BOM through decode and encode", () => {
    const withBom = b64([0xef, 0xbb, 0xbf, 0x3b, 0x20, 0x61, 0x0a]);
    expect(isLosslessLedgerFileContent(withBom, "base64")).toBe(true);
    expect(
      encodeLedgerFileContent(decodeLedgerFileContent(withBom, "base64")),
    ).toBe(withBom);
  });

  it("treats content the API sent as text as already decoded", () => {
    expect(isLosslessLedgerFileContent("; plain", null)).toBe(true);
  });
});

describe("the file editor", () => {
  // The screen runs queries this runner cannot execute, so the wiring is
  // checked on its source: both the first load and Reload decide read-only.
  const source = require("fs").readFileSync(
    require("path").join(
      __dirname,
      "..",
      "..",
      "screens",
      "ledger-file-editor-screen",
      "index.tsx",
    ),
    "utf8",
  ) as string;

  it("opens a file that does not round-trip read-only, on load and reload", () => {
    expect(
      source.split("setLossy(!isLosslessLedgerFileContent(raw, enc));").length -
        1,
    ).toBe(2);
    // And one the server sent no text for (w21/185).
    expect(
      source.includes(
        "const canWrite = canWriteLedger && !lossy && !tooLarge && !overLimit;",
      ),
    ).toBe(true);
  });
});

// w21/062: the editor joins lines with "\n", so saving a CRLF file rewrote
// every line ending and a one-line edit became a whole-file diff.
describe("line endings survive an edit", () => {
  const b64 = (text: string) => Buffer.from(text, "utf8").toString("base64");
  // What the CodeMirror document hands back: its lines joined with "\n".
  const editor = (text: string) => text.split(/\r\n|\r|\n/).join("\n");
  const roundTrip = (original: string, edit: (text: string) => string) => {
    const decoded = decodeLedgerFileContent(b64(original), "base64");
    const saved = encodeLedgerFileContent(
      withLineEnding(edit(editor(decoded)), lineEndingOf(decoded)),
    );
    return Buffer.from(saved, "base64").toString("utf8");
  };
  const addLine = (text: string) => `${text}; qa added`;

  it("keeps a CRLF file's endings, so only the added line changes", () => {
    expect(roundTrip("; line1\r\n; line2\r\n; line3\r\n", addLine)).toBe(
      "; line1\r\n; line2\r\n; line3\r\n; qa added",
    );
  });

  it("leaves an LF file as it was", () => {
    expect(roundTrip("; line1\n; line2\n", addLine)).toBe(
      "; line1\n; line2\n; qa added",
    );
  });

  it("keeps a BOM and CRLF together", () => {
    expect(roundTrip("﻿; a\r\n; b\r\n", (text) => text)).toBe(
      "﻿; a\r\n; b\r\n",
    );
  });

  it("keeps a mixed file's majority ending", () => {
    expect(lineEndingOf("a\r\nb\r\nc\n")).toBe("\r\n");
    expect(lineEndingOf("a\nb\nc\r\n")).toBe("\n");
    expect(lineEndingOf("no newline")).toBe("\n");
  });

  it("is what the editor saves with, from load and from Reload", () => {
    const source = require("fs").readFileSync(
      require("path").join(
        __dirname,
        "..",
        "..",
        "screens",
        "ledger-file-editor-screen",
        "index.tsx",
      ),
      "utf8",
    ) as string;
    expect(
      source.split("lineEndingRef.current = lineEndingOf(fc);").length - 1,
    ).toBe(2);
    expect(
      source.includes("withLineEnding(content, lineEndingRef.current)"),
    ).toBe(true);
  });
});

// w21/185: Gitea sends `content: null` for a blob over its inline limit, which
// opened as an empty, writable document.
describe("isUnreadableLargeFile", () => {
  it("flags a non-empty file that came back without its text", () => {
    expect(isUnreadableLargeFile(null, 11_000_000)).toBe(true);
    expect(isUnreadableLargeFile("", 11_000_000)).toBe(true);
    expect(isUnreadableLargeFile(undefined, 12)).toBe(true);
  });

  it("leaves an empty file, and a file with its text, alone", () => {
    expect(isUnreadableLargeFile(null, 0)).toBe(false);
    expect(isUnreadableLargeFile("", 0)).toBe(false);
    expect(isUnreadableLargeFile(null, null)).toBe(false);
    expect(isUnreadableLargeFile("2026-01-01 open Assets:Cash", 27)).toBe(
      false,
    );
  });

  it("is what the editor opens read-only on, at load and on reload", () => {
    const editor = require("fs").readFileSync(
      require("path").join(
        __dirname,
        "..",
        "..",
        "screens",
        "ledger-file-editor-screen",
        "index.tsx",
      ),
      "utf8",
    );
    expect(editor.split("isUnreadableLargeFile(").length - 1).toBe(2);
    expect(editor.includes("canWriteLedger && !lossy && !tooLarge")).toBe(true);
  });
});

// w21/186: a file between 1 and 10 MiB opened writable, and every save was
// refused after the edit.
describe("isOverEditLimit", () => {
  it("is over 1 MiB, exactly", () => {
    expect(isOverEditLimit(1_048_576)).toBe(false);
    expect(isOverEditLimit(1_048_577)).toBe(true);
    expect(isOverEditLimit(1_300_000)).toBe(true);
    expect(isOverEditLimit(null)).toBe(false);
  });

  it("opens the editor read-only with its own notice, on load and reload", () => {
    const editor = require("fs").readFileSync(
      require("path").join(
        __dirname,
        "..",
        "..",
        "screens",
        "ledger-file-editor-screen",
        "index.tsx",
      ),
      "utf8",
    );
    expect(editor.split("setOverLimit(isOverEditLimit(").length - 1).toBe(2);
    expect(editor.includes('"ledgerEditorTooLargeToEdit"')).toBe(true);
  });
});
