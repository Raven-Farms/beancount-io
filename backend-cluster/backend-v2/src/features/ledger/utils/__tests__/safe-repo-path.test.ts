import { BadUserInputError } from "@/shared/errors";
import { assertSafeRepoPath } from "@/features/ledger/utils/safe-repo-path";
import {
  archiveRef,
  assertSafeArchiveName,
} from "@/features/ledger/utils/safe-archive-name";

describe("repository path validation", () => {
  it.each(["main.bean", "accounts/2026.bean", "Q1 #draft.bean"])(
    "accepts %p",
    (path) => expect(() => assertSafeRepoPath(path)).not.toThrow(),
  );

  it.each([
    "",
    "/main.bean",
    "dir//main.bean",
    "./main.bean",
    "../private/main.bean",
    "dir/../../private/main.bean",
    "dir\\main.bean",
    "dir/\0main.bean",
  ])("rejects %p", (path) => {
    expect(() => assertSafeRepoPath(path)).toThrow(BadUserInputError);
  });
});

describe("archive name validation", () => {
  it.each(["main.zip", "v1.0.tar.gz", "gitea-main.zip"])(
    "accepts %p",
    (archive) => {
      expect(() => assertSafeArchiveName(archive)).not.toThrow();
    },
  );

  // Gitea refuses these upstream; they were reported as an outage (w23/003).
  it.each(["main", "main.rar", "main.tar", "zip", "tar.gz", "main.bundle"])(
    "refuses %p, which names no supported format",
    (archive) => {
      expect(() => assertSafeArchiveName(archive)).toThrow(
        /\.zip or \.tar\.gz/,
      );
    },
  );

  it.each([
    ["main.zip", "main"],
    ["v1.0.tar.gz", "v1.0"],
    ["release.zip.tar.gz", "release.zip"],
  ])("reads the reference of %p as %p", (archive, ref) => {
    expect(archiveRef(archive)).toBe(ref);
  });

  it.each(["", ".", "..", "../private", "a/b", "a%2fb", "a?ref=main"])(
    "rejects %p",
    (archive) => {
      expect(() => assertSafeArchiveName(archive)).toThrow(BadUserInputError);
    },
  );
});
