import {
  decodeLedgerFileContent,
  encodeLedgerFileContent,
  isLosslessLedgerFileContent,
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
    expect(source.includes("const canWrite = canWriteLedger && !lossy;")).toBe(
      true,
    );
  });
});
