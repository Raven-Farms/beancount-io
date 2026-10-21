import fs from "fs";
import path from "path";
import { receiptCanRetry } from "../receipt-utils";

// w21/204: "Upload failed. Please try again." offered only Cancel and Retake,
// and Retake threw the photo away, so a network blip lost the scan.
describe("retrying a failed receipt upload", () => {
  it("offers a retry for every failure except a spent AI quota", () => {
    for (const code of [
      "upload_failed",
      "upload_url_failed",
      "upload_url_timeout",
      "upload_s3_timeout",
      "parse_failed",
    ]) {
      expect(receiptCanRetry(code)).toBe(true);
    }
    expect(receiptCanRetry("quota_exhausted")).toBe(false);
  });

  it("re-runs the upload with the photo already taken", () => {
    const source = fs
      .readFileSync(
        path.join(__dirname, "..", "receipt-capture-screen.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    // The retry is the upload handler, not the reset that Retake performs.
    expect(
      source.includes(
        "consthandleRetry=()=>{failed.current=false;handleUpload();};",
      ),
    ).toBe(true);
    expect(
      source.includes('onRetry={phase.kind==="error"&&receiptCanRetry'),
    ).toBe(true);
  });

  it("renders the button on the error screen", () => {
    const source = fs.readFileSync(
      path.join(__dirname, "..", "preview-view.tsx"),
      "utf8",
    );
    expect(source.includes('testID="receipt-error-retry"')).toBe(true);
  });
});
