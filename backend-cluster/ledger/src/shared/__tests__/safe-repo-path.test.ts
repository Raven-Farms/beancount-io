import { BadUserInputError } from "@/shared/errors";
import {
  assertPortableRepoPath,
  assertSafeRepoPath,
  toSafeRepoUrlPath,
} from "@/shared/safe-repo-path";

describe("safe repository URL paths", () => {
  it("encodes each legitimate path segment", () => {
    expect(toSafeRepoUrlPath("reports/Q1 #draft.bean")).toBe(
      "reports/Q1%20%23draft.bean",
    );
  });

  it.each([
    "",
    "/main.bean",
    "dir//main.bean",
    "./main.bean",
    "../private/main.bean",
    "dir/../../private/main.bean",
    "dir\\main.bean",
    "dir/\0main.bean",
  ])("rejects unsafe path %p", (path) => {
    expect(() => assertSafeRepoPath(path)).toThrow(BadUserInputError);
  });

  it.each([".git", ".Git/config", "sub/.GIT/x.bean"])(
    "refuses %p, which is inside .git",
    (path) => {
      expect(() => toSafeRepoUrlPath(path)).toThrow(/inside \.git/);
    },
  );

  it.each([".gitignore", ".github/ci.yml", ".gitx/a.bean", "sub/.git.bean"])(
    "accepts %p, whose segment only starts with .git",
    (path) => {
      expect(() => assertSafeRepoPath(path)).not.toThrow();
    },
  );

  it("double-encodes a percent-encoded traversal so it remains a filename", () => {
    expect(toSafeRepoUrlPath("%2e%2e/private.bean")).toBe(
      "%252e%252e/private.bean",
    );
  });
});

// w23/054: the ledger service repeats the rule for new files.
describe("portable paths for new files", () => {
  it.each([
    ["qa\nx.bean", "control character"],
    ["qa\tx.bean", "control character"],
    ["qa\u001bx.bean", "control character"],
    ["qa\u2028x.bean", "control character"],
    ["qa\u202ex.bean", "bidirectional"],
    ["a:b.bean", "Windows cannot store"],
    ["q?.bean", "Windows cannot store"],
    ['say"hi".bean', "Windows cannot store"],
    ["CON", "device name"],
    ["aux.bean", "device name"],
    ["dir/NUL.bean", "device name"],
    ["Lpt9.txt", "device name"],
    ["qa-x./y.bean", "ending in a dot or a space"],
    ["qa-x /y.bean", "ending in a dot or a space"],
    [`${"x".repeat(252)}.bean`, "longer than 255 bytes"],
  ])("refuses %j: %s", (path, rule) => {
    expect(() => assertPortableRepoPath(path)).toThrow(rule);
  });

  it.each([
    "main.bean",
    "2026/imports.bean",
    ".gitignore",
    "Café.bean",
    "Cafe\u0301.bean",
    "资产.bean",
    "auxiliary.bean",
    "my file.bean",
  ])("accepts %j", (path) => {
    expect(() => assertPortableRepoPath(path)).not.toThrow();
  });
});
