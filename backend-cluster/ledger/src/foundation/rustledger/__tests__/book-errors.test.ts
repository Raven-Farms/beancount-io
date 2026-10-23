import type { BeancountError } from "@rustledger/wasm";
import { locateBookErrors } from "../book-errors";

// w21/534: booking and interpolation errors had no file or line, so the app
// could not open them. The messages are the engine's own for the note's
// fixtures.
const book = (message: string): BeancountError => ({
  message,
  code: "BOOK",
  phase: "validate",
  hint: null,
  file: null,
  line: null,
  column: null,
  end_line: null,
  end_column: null,
  severity: "error",
});

const main = [
  'option "operating_currency" "USD"',
  "2025-01-01 open Assets:QaBroker2 USD,HOOL",
  "",
  '2026-01-05 * "Cafe" "qa cost and elided"',
  "  Assets:QaBroker2 10 HOOL {}",
  "  Assets:Cash",
  "",
  '2026-01-06 * "Shop" "bare at at"',
  "  Assets:QaBroker2 10 HOOL @@",
  "  Assets:Cash",
  '2026-01-07 * "Gap"',
  "  Expenses:X",
  "  Assets:Cash",
].join("\n");

describe("locateBookErrors", () => {
  it("puts an interpolation error on its transaction's first line", () => {
    const [located] = locateBookErrors(
      [
        book(
          'interpolation failed: cannot infer currency for posting to account Assets:Cash (2026-01-05, "qa cost and elided")',
        ),
      ],
      { "main.bean": main },
      "main.bean",
    );
    expect(located).toMatchObject({ file: "main.bean", line: 4, column: 1 });
    expect(located.code).toBe("BOOK");
  });

  it("locates a bare @@ price and a payeeless entry", () => {
    const located = locateBookErrors(
      [
        book(
          "interpolation failed: cannot tell which currency the bare price on the Assets:QaBroker2 posting should be computed in; write the price currency (e.g. `@ 1.20 USD`) (2026-01-06, \"bare at at\")",
        ),
        book(
          'interpolation failed: cannot infer currency for posting to account Expenses:X (2026-01-07, "Gap")',
        ),
      ],
      { "main.bean": main },
      "main.bean",
    );
    expect(located.map((error) => error.line)).toEqual([8, 11]);
  });

  it("finds a transaction in an included file", () => {
    const [located] = locateBookErrors(
      [book('interpolation failed: x (2026-02-01, "Rent")')],
      {
        "main.bean": 'include "sub/a.bean"',
        "sub/a.bean": '\n\n2026-02-01 * "Rent"\n  A 1 USD',
      },
      "main.bean",
    );
    expect(located).toMatchObject({ file: "sub/a.bean", line: 3 });
  });

  it("pairs same-day twins in order and leaves an unmatched count alone", () => {
    const twins = {
      "main.bean": '2026-03-01 * "Dup"\n  A\n2026-03-01 * "Dup"\n  A',
    };
    const message = 'interpolation failed: x (2026-03-01, "Dup")';
    expect(
      locateBookErrors([book(message), book(message)], twins, "main.bean").map(
        (error) => error.line,
      ),
    ).toEqual([1, 3]);
    expect(
      locateBookErrors([book(message)], twins, "main.bean")[0].line,
    ).toBeNull();
  });

  it("leaves other errors and located ones as they were", () => {
    const other = { ...book("something"), code: "E1001" };
    const located = { ...book('x (2026-01-05, "qa cost and elided")'), file: "main.bean", line: 99 };
    expect(
      locateBookErrors([other, located], { "main.bean": main }, "main.bean"),
    ).toEqual([other, located]);
  });
});
