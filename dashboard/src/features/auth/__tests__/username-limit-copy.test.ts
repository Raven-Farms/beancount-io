import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { USERNAME_MAX_LENGTH } from "@/common/lib/auth/username-rule";
import { numbersIn } from "@/test/locale-scan";

/**
 * The signup form enforces a 20-character username, but twelve catalogs still
 * promised 16 — a visitor reading Chinese was told their 17-character name was
 * too long and given a boundary that did not exist. Several of those strings
 * were also half-English ("Benutzername must be at most 16 characters").
 *
 * These cases read the real validator and the real catalogs, so copy that
 * drifts from the rule it describes fails here rather than only in a browser.
 */

const AUTH_LOCALES = join(import.meta.dirname, "..", "locales");
const REGISTER_FORM = join(
  import.meta.dirname,
  "..",
  "components",
  "register-form",
  "index.tsx",
);

/**
 * The maximum the form actually enforces: the shared rule's, which the
 * schema must be the one to apply (Settings' rename uses it too, w0/047).
 */
function enforcedMaximum(): number {
  const source = readFileSync(REGISTER_FORM, "utf8");
  expect(
    source,
    "the register form must apply the shared username maximum",
  ).toMatch(/\.max\(USERNAME_MAX_LENGTH,\s*t\("auth\.usernameMaxLength"\)\)/);
  return USERNAME_MAX_LENGTH;
}

function localeFiles(): string[] {
  return readdirSync(AUTH_LOCALES).filter((name) => name.endsWith(".ts"));
}

function message(file: string, key: string): string {
  const source = readFileSync(join(AUTH_LOCALES, file), "utf8");
  const pattern = new RegExp(
    `"${key}": \\{\\s*\\n\\s*message:\\s*"((?:[^"\\\\]|\\\\.)*)"`,
  );
  const match = pattern.exec(source);
  expect(match, `${file} is missing ${key}`).not.toBeNull();
  return match![1];
}

describe("username length copy", () => {
  const maximum = enforcedMaximum();

  it("is the twenty the form enforces", () => {
    expect(maximum).toBe(20);
  });

  it.each(localeFiles())(
    "%s states the enforced maximum in its too-long error",
    (file) => {
      expect(numbersIn(message(file, "auth.usernameMaxLength"))).toContain(
        maximum,
      );
    },
  );

  it.each(localeFiles())(
    "%s states the enforced maximum in its placeholder",
    (file) => {
      expect(numbersIn(message(file, "auth.enterUsername"))).toContain(maximum);
    },
  );

  it.each(localeFiles())("%s quotes no other length", (file) => {
    // 16 was the stale promise; any stray number would be a new mismatch.
    for (const key of ["auth.usernameMaxLength", "auth.enterUsername"]) {
      for (const value of numbersIn(message(file, key))) {
        expect(value).toBe(maximum);
      }
    }
  });

  it.each(localeFiles().filter((file) => file !== "en.ts"))(
    "%s is translated rather than half English",
    (file) => {
      // A bad find-and-replace left strings like "Benutzername must be at
      // most 16 characters" in several catalogs.
      expect(message(file, "auth.usernameMaxLength")).not.toMatch(
        /must be at most/i,
      );
    },
  );
});
