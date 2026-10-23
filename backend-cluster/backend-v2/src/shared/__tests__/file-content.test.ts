import { decodeFileContent } from "@/shared/file-content";

const base64 = (...parts: (string | number[])[]) => ({
  encoding: "base64",
  content: Buffer.concat(
    parts.map((part) =>
      typeof part === "string" ? Buffer.from(part) : Buffer.from(part),
    ),
  ).toString("base64"),
});

describe("decodeFileContent", () => {
  it.each([
    ["ASCII", base64("; a\n"), "; a\n"],
    ["multi-byte UTF-8", base64("; Café ☕\n"), "; Café ☕\n"],
    ["a byte-order mark, kept", base64([0xef, 0xbb, 0xbf], "; a"), "﻿; a"],
    ["plain text", { content: "; a\n" }, "; a\n"],
    ["nothing", { content: null }, ""],
  ])("reads %s as exact text", (_case, file, content) => {
    expect(decodeFileContent(file)).toEqual({ content, lossy: false });
  });

  // w23/030: these used to read as clean text that, written back, replaced
  // the undecodable bytes with U+FFFD.
  it.each([
    ["a Latin-1 byte", base64("; Caf", [0xe9], "\n")],
    ["a truncated sequence", base64("; ", [0xe2, 0x98])],
    ["an overlong encoding", base64([0xc0, 0xaf])],
  ])("marks %s lossy", (_case, file) => {
    expect(decodeFileContent(file)).toMatchObject({ lossy: true });
  });
});
