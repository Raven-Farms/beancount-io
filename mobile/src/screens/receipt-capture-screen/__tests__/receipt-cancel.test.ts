import fs from "fs";
import path from "path";
import { createIdleGuard, uploadPercent } from "../upload-guard";

const read = (file: string) =>
  fs.readFileSync(path.join(__dirname, "..", file), "utf8").replace(/\s+/g, "");
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// w21/205: the upload had no Cancel and a 60 s whole-transfer limit that cut
// off slow but working uploads.
describe("receipt upload limit", () => {
  it("fires only after silence, and a touch postpones it", async () => {
    let idle = 0;
    const guard = createIdleGuard(60, () => (idle += 1));
    guard.touch();
    await sleep(40);
    guard.touch(); // bytes moved: the clock restarts
    await sleep(40);
    expect(idle).toBe(0);
    await sleep(60);
    expect(idle).toBe(1);
  });

  it("does not fire once stopped", async () => {
    let idle = 0;
    const guard = createIdleGuard(20, () => (idle += 1));
    guard.touch();
    guard.stop();
    await sleep(50);
    expect(idle).toBe(0);
  });

  it("reports whole percent, or null while the size is unknown", () => {
    expect(
      uploadPercent({ totalBytesSent: 1, totalBytesExpectedToSend: 3 }),
    ).toBe(33);
    expect(
      uploadPercent({ totalBytesSent: 9, totalBytesExpectedToSend: 3 }),
    ).toBe(100);
    expect(
      uploadPercent({ totalBytesSent: 5, totalBytesExpectedToSend: -1 }),
    ).toBe(null);
    expect(
      uploadPercent({ totalBytesSent: 0, totalBytesExpectedToSend: 0 }),
    ).toBe(null);
  });
});

describe("cancelling a receipt upload", () => {
  it("offers Cancel on the busy overlay and wires it to the workflow", () => {
    expect(
      read("preview-view.tsx").includes('testID="receipt-busy-cancel"'),
    ).toBe(true);
    expect(
      read("receipt-capture-screen.tsx").includes(
        "onCancelBusy={workflow.cancel}",
      ),
    ).toBe(true);
  });

  it("aborts the request and the transfer, and ignores late results", () => {
    const source = read("use-receipt-workflow.ts");
    for (const piece of [
      "run.abort.abort();",
      "run.upload?.cancelAsync()",
      "if(!live())return;",
      "FileSystem.createUploadTask(",
    ]) {
      expect(source.includes(piece)).toBe(true);
    }
    // The whole-transfer race is gone.
    expect(source.includes("60_000")).toBe(false);
  });
});
