import fs from "fs";
import path from "path";

/**
 * w21/403: Scan Receipt mounts `<StatusBar style="light" />`; popped on leaving,
 * RN's default left Android's icons white on the light header. A base bar in the
 * root layout is what it pops back to. Source checks: both need the runtime.
 */
const read = (...parts: string[]) =>
  fs
    .readFileSync(path.join(__dirname, "..", "..", ...parts), "utf8")
    .replace(/\s+/g, "");

describe("the status bar", () => {
  it("has a theme-following base bar in the root layout, inside the providers", () => {
    const layout = read("app", "_layout.tsx");
    expect(layout.includes('import{StatusBar}from"expo-status-bar";')).toBe(
      true,
    );
    const providers = layout.indexOf("<Providers>");
    const bar = layout.indexOf('<StatusBarstyle="auto"/>');
    const end = layout.indexOf("</Providers>");
    expect(providers > -1 && bar > providers && bar < end).toBe(true);
  });

  it("is the only other place a status bar is set, apart from the camera's light one", () => {
    const srcDir = path.join(__dirname, "..");
    const offenders: string[] = [];
    const walk = (dir: string) => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          if (entry.name !== "__tests__") walk(full);
        } else if (
          /\.tsx?$/.test(entry.name) &&
          /<StatusBar\b/.test(fs.readFileSync(full, "utf8"))
        ) {
          offenders.push(path.relative(srcDir, full));
        }
      }
    };
    walk(srcDir);
    expect(offenders).toEqual([
      path.join(
        "screens",
        "receipt-capture-screen",
        "receipt-capture-screen.tsx",
      ),
    ]);
  });
});
