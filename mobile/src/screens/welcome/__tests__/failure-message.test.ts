import fs from "fs";
import path from "path";
import { signInFailureMessageKey } from "../failure-message";

// w21/634: the example drawer said "Could not complete sign-in" for every
// failure, offline included, where Welcome names the server problem.
describe("signInFailureMessageKey", () => {
  it("names a server problem as one", () => {
    const key = (reason: never) =>
      signInFailureMessageKey({ flow: "sign_in", reason });
    expect(key("unreachable" as never)).toBe("serverConnectionUnreachable");
    expect(key("timeout" as never)).toBe("serverConnectionTimeout");
    expect(key("incompatible" as never)).toBe("serverConnectionIncompatible");
    expect(key("not_configured" as never)).toBe(
      "serverConnectionNotConfigured",
    );
    expect(key("mismatch" as never)).toBe("serverConnectionMismatch");
  });

  it("blames the sign-in or sign-up only for a rejection", () => {
    expect(
      signInFailureMessageKey({ flow: "sign_in", reason: "rejected" }),
    ).toBe("signInFailed");
    expect(
      signInFailureMessageKey({ flow: "sign_up", reason: "rejected" }),
    ).toBe("signUpFailed");
  });
});

describe("the example drawer's sign-in failure", () => {
  const read = (...parts: string[]) =>
    fs
      .readFileSync(path.join(__dirname, "..", "..", ...parts), "utf8")
      .replace(/\s+/g, "");

  it("uses the shared reason mapping for the toast and the drawer line", () => {
    const layout = read("examples", "examples-layout.tsx");
    expect(
      layout.includes(
        "constfailureMessage=failure?t(signInFailureMessageKey(failure)):null;",
      ),
    ).toBe(true);
    expect(layout.includes("signInFailure:failureMessage,")).toBe(true);
    expect(
      read("..", "components", "ledger-drawer", "ledger-drawer.tsx").includes(
        "{guest.signInFailure&&(<InlineErrorstyle={styles.stateText}message={guest.signInFailure}/>)}",
      ),
    ).toBe(true);
  });
});
