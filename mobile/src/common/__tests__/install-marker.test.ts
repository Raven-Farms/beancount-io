import fs from "fs";
import path from "path";
import { claimInstallMarker, type SandboxStorage } from "../install-marker";

/**
 * w21/154: iOS keeps Keychain items across an uninstall, so a reinstall
 * restored the previous account's session.
 */
function sandbox(initial: Record<string, string>): SandboxStorage & {
  values: Record<string, string>;
} {
  const values = { ...initial };
  return {
    values,
    getItem: async (key) => values[key] ?? null,
    setItem: async (key, value) => {
      values[key] = value;
    },
    getAllKeys: async () => Object.keys(values),
  };
}

describe("claimInstallMarker", () => {
  it("calls an empty sandbox a fresh install, once", async () => {
    const storage = sandbox({});
    expect(await claimInstallMarker(storage)).toBe("fresh-install");
    expect(await claimInstallMarker(storage)).toBe("known");
  });

  it("keeps an install from before the marker existed signed in", async () => {
    const storage = sandbox({ ledger: '"alice/books"' });
    expect(await claimInstallMarker(storage)).toBe("known");
    expect(Object.keys(storage.values).sort()).toEqual([
      "install-marker",
      "ledger",
    ]);
  });

  it("drops the Keychain session at launch before anything restores it", () => {
    const splash = fs
      .readFileSync(
        path.join(
          __dirname,
          "..",
          "providers",
          "splash-provider",
          "splash-provider.tsx",
        ),
        "utf8",
      )
      .replace(/\s+/gu, "");
    const check = splash.indexOf(
      'if((awaitclaimInstallMarker(AsyncStorage))==="fresh-install"){awaitforgetSessionFromPreviousInstall()',
    );
    expect(check > -1).toBe(true);
    expect(check < splash.indexOf("loadSession(),")).toBe(true);
  });

  // w21/318: a reinstall that found a stored session left the browser's cookies
  // for it, so the first Sign In still offered its one-tap Approve.
  it("asks for an account choice at the next Sign In when it found a session", () => {
    const session = fs
      .readFileSync(path.join(__dirname, "..", "vars", "session.ts"), "utf8")
      .replace(/\s+/gu, "");
    const forget = session.slice(
      session.indexOf("exportasyncfunctionforgetSessionFromPreviousInstall"),
    );
    const found = forget.indexOf("if(stored===null)return;");
    const mark = forget.indexOf(
      "awaitmarkAccountChoiceNeeded().catch(()=>undefined);",
    );
    const deleted = forget.indexOf(
      'awaitSecureStore.deleteItemAsync("session")',
    );
    expect(found > -1 && mark > found).toBe(true);
    // Marked before the session is dropped, and only when there was one.
    expect(mark < deleted).toBe(true);
  });
});
