import {
  errorHint,
  errorMessageWithHint,
} from "../../../common/new-ledger-error";
import { fileBannerErrors } from "../utils";

// w21/521: the editor's banner dropped the fix hint Notifications shows.
describe("the file editor's error banner rows", () => {
  const hint =
    "Re-save the file as UTF-8, or remove the include that reaches it.";
  const errors = [
    {
      message: "Invalid encoding",
      lineno: 1,
      filename: "qa-latin1.bean",
      hint,
    },
    { message: "Elsewhere", lineno: 2, filename: "other.bean", hint: "no" },
  ];

  it("keep the engine's hint, so the row shows and reads it", () => {
    const rows = fileBannerErrors(errors, "qa-latin1.bean");
    expect(rows.length).toBe(1);
    expect(errorHint(rows[0])).toBe(hint);
    expect(errorMessageWithHint(rows[0]).includes(hint)).toBe(true);
  });

  it("have no hint when the engine gave none", () => {
    const rows = fileBannerErrors(
      [{ message: "Oops", lineno: 3, filename: "a.bean" }],
      "a.bean",
    );
    expect(errorHint(rows[0])).toBe(null);
  });
});
