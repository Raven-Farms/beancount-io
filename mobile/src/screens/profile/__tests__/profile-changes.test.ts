import {
  profileChanges,
  usernameAllowed,
  usernameErrorKey,
} from "../profile-changes";

const saved = { firstName: "Ada", lastName: "", username: "ada" };

describe("profileChanges", () => {
  it("writes nothing for an untouched or whitespace-only edit", () => {
    expect(profileChanges(saved, { ...saved })).toEqual({});
    expect(
      profileChanges(saved, { ...saved, firstName: " Ada ", username: "ada " }),
    ).toEqual({});
  });

  it("sends both names when either changes, since the API clears a missing one", () => {
    expect(profileChanges(saved, { ...saved, lastName: " Lovelace" })).toEqual({
      name: { firstName: "Ada", lastName: "Lovelace" },
    });
  });

  it("renames only when the username changed", () => {
    expect(profileChanges(saved, { ...saved, username: "lovelace" })).toEqual({
      username: "lovelace",
    });
  });
});

const apiError = (code: string, message = "refused") => ({
  graphQLErrors: [{ message, extensions: { code } }],
});

describe("usernameErrorKey", () => {
  it("reads the API's CONFLICT code as a taken username", () => {
    expect(
      usernameErrorKey(apiError("CONFLICT", "Username conflict: lovelace")),
    ).toBe("profileUsernameTaken");
  });

  it("reads BAD_USER_INPUT as a name outside the rule, on the field", () => {
    // Refused renames used to land in the generic "Failed to save" (w0/036).
    expect(usernameErrorKey(apiError("BAD_USER_INPUT"))).toBe(
      "profileUsernameRule",
    );
  });

  it("does not guess from message text", () => {
    // A merge conflict or any other failure mentioning "conflict" is not a
    // taken username; only the typed code says so.
    expect(usernameErrorKey(new Error("Username conflict: lovelace"))).toBe(
      null,
    );
    expect(
      usernameErrorKey(apiError("INTERNAL_SERVER_ERROR", "conflict")),
    ).toBe(null);
    expect(usernameErrorKey(undefined)).toBe(null);
  });
});

describe("usernameAllowed", () => {
  // Sign-up's rule: 1–20 of a–z, 0–9 and underscore (w0/036).
  it("accepts a new name inside the rule", () => {
    for (const name of ["lovelace", "ada_1815", "a", "a".repeat(20)]) {
      expect(usernameAllowed("ada", name)).toBe(true);
    }
  });

  it("refuses a new name sign-up would refuse", () => {
    for (const name of [
      "José",
      "Ada",
      "ada.lovelace",
      "ada-lovelace",
      "ada lovelace",
      "a".repeat(21),
    ]) {
      expect(usernameAllowed("ada", name)).toBe(false);
    }
  });

  it("trims before checking, as the save does", () => {
    expect(usernameAllowed("ada", "  lovelace ")).toBe(true);
  });

  it("lets an unchanged name that predates the rule be saved", () => {
    expect(usernameAllowed("john.doe", "john.doe")).toBe(true);
    expect(usernameAllowed("john.doe", " john.doe ")).toBe(true);
    expect(usernameAllowed("john.doe", "john.doe2")).toBe(false);
  });
});
