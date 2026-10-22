import { BadUserInputError } from "@/shared/errors";
import { assertSafeRepoPath, toSafeRepoUrlPath } from "@/shared/safe-repo-path";

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
