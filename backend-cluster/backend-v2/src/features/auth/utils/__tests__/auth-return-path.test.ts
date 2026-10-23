import { validateAuthReturnPath } from "../auth-return-path";
import { BadUserInputError } from "@/shared/errors";

it.each([
  "/settings/api-keys?lang=en#ssh-keys",
  "/ledger/owner/My%20Ledger#top",
  "/ledger/owner/books/query?q=SELECT%20account%0AFROM%20accounts",
  "/ledger/owner/books/query?q=SELECT%20%5C%22name%5C%22",
  "/ledger/owner/books/files?path=reports%2F2026.bean",
  "/ledger/owner/books/files?path=100%",
  "/ledger#fragment%0Aencoded",
])("preserves the legitimate encoded continuation %s", (value) => {
  expect(validateAuthReturnPath(value)).toBe(value);
});

it.each([
  "https://evil.example/x",
  "//evil.example",
  "/\\evil.example",
  "relative/path",
  "/\t/evil.example",
  "/\n/evil.example",
  "/\r/evil.example",
  "/\u0000/evil.example",
  "/\u007f/evil.example",
  "/%09/evil.example",
  "/%0d/evil.example",
  "/%0A/evil.example",
  "/%00/evil.example",
  "/%5cevil.example",
  "/%5Cevil.example",
  "/%2f%2fevil.example",
  "/%2509/evil.example",
  "/%252f%252fevil.example",
  "/ledger/..%2f%2fevil.example",
  "/%09/evil.example?q=100%",
  "/%zz/%09/evil.example",
  "/ledger%2525252520x",
  "/ledger\\file",
  "/ledger/%255cfile",
])("rejects the unsafe path %s", (value) => {
  expect(() => validateAuthReturnPath(value)).toThrow(BadUserInputError);
});

it("treats absent/empty continuation as absent and canonicalizes legal dot segments", () => {
  expect(validateAuthReturnPath()).toBeUndefined();
  expect(validateAuthReturnPath("")).toBeUndefined();
  expect(validateAuthReturnPath("/ledger/../settings?lang=en#keys")).toBe(
    "/settings?lang=en#keys",
  );
});

it("enforces the length bound on input and canonical encoded output", () => {
  expect(validateAuthReturnPath("/" + "a".repeat(2047))).toHaveLength(2048);
  expect(() => validateAuthReturnPath("/" + "a".repeat(2048))).toThrow(
    BadUserInputError,
  );
  expect(() => validateAuthReturnPath("/" + "界".repeat(300))).toThrow(
    BadUserInputError,
  );
});

it("keeps a complete fragment inside the canonical next query parameter", () => {
  const next = validateAuthReturnPath(
    "/ledger/books/query?q=SELECT%0A1#results",
  );
  const url = new URL("https://example.com/auth/login/");
  url.searchParams.set("next", next!);
  expect(url.hash).toBe("");
  expect(url.searchParams.get("next")).toBe(next);
});
