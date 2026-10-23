import { diffBeanCheckErrors } from "@/features/ledger/utils/bean-check-errors";

const error = (message: string, source?: string) => ({
  message,
  ...(source && { source }),
});

describe("diffBeanCheckErrors", () => {
  // w23/034: a write that shifts lines moves every error below it.
  it("does not count an existing error that moved to another line", () => {
    expect(
      diffBeanCheckErrors(
        [error("Document file not found: a.pdf", "main.bean:93")],
        [error("Document file not found: a.pdf", "main.bean:97")],
      ),
    ).toEqual([]);
  });

  it("counts a second copy of a known message as new", () => {
    const known = error("Duplicate open", "main.bean:3");
    const copy = error("Duplicate open", "main.bean:40");
    expect(diffBeanCheckErrors([known], [known, copy])).toEqual([copy]);
  });

  it("counts the same message in another file as new", () => {
    const moved = error("Duplicate open", "txns/2026.bean:3");
    expect(
      diffBeanCheckErrors([error("Duplicate open", "main.bean:3")], [moved]),
    ).toEqual([moved]);
  });

  it("ignores the entry tag a re-dated or renamed entry rewrites", () => {
    expect(
      diffBeanCheckErrors(
        [error('Cannot interpolate (2026-08-30, "Groceries")', "main.bean:9")],
        [error('Cannot interpolate (2026-08-31, "Food")', "main.bean:9")],
      ),
    ).toEqual([]);
  });

  it("keeps a file name that itself contains a colon", () => {
    const other = error("Bad", "a:b.bean:2");
    expect(diffBeanCheckErrors([error("Bad", "a.bean:2")], [other])).toEqual([
      other,
    ]);
  });
});
