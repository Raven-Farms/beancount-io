import fs from "fs";
import path from "path";

// w21/454: Welcome stays mounted under the Server screen, so a failure already
// settled outlived a changed server, and VoiceOver never announced it. The hook
// runs React effects this runner cannot execute, so the wiring is checked on its
// source.
const read = (file: string) =>
  fs.readFileSync(path.join(__dirname, "..", file), "utf8").replace(/\s+/g, "");

describe("a settled sign-in failure", () => {
  it("is cleared when the server changes, before the in-flight check", () => {
    const hook = read("use-native-sign-in.ts");
    const effect = hook.slice(hook.indexOf("lastServer.current=server;"));
    const clear = effect.indexOf("setFailure(null);");
    expect(clear > -1).toBe(true);
    expect(clear < effect.indexOf("if(!running.current)return;")).toBe(true);
  });

  it("is announced to a screen reader", () => {
    expect(
      read("index.tsx").includes(
        "<InlineErrorstyle={styles.error}message={t(signInFailureMessageKey(failure))}/>",
      ),
    ).toBe(true);
  });
});
