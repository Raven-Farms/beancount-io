import {
  detectRecurrence,
  type SeriesPoint,
} from "../screens/merchants-screen/selectors/detect-recurrence";

// w21/271: one weekend-shifted payment turned off the day-of-month anchor, so
// Next drifted a day.
const on = (dates: string[]): SeriesPoint[] =>
  dates.map((date) => ({ date, currency: "USD", amount: -50 }));
const TODAY = "2026-10-21";

const FIRST = [
  "2025-11-01",
  "2025-12-01",
  "2026-01-01",
  "2026-02-01",
  "2026-03-02",
  "2026-04-01",
  "2026-05-01",
  "2026-06-01",
  "2026-07-01",
  "2026-08-01",
  "2026-09-01",
  "2026-10-01",
];

describe("one shifted payment does not move Next", () => {
  it("predicts the 1st with March paid on the 2nd", () => {
    expect(detectRecurrence(on(FIRST), TODAY)!.nextExpected).toBe("2026-11-01");
  });

  it("predicts the 25th with December paid on the 26th", () => {
    const dates = [
      "2025-11-25",
      "2025-12-26",
      "2026-01-25",
      "2026-02-25",
      "2026-03-25",
      "2026-04-25",
      "2026-05-25",
      "2026-06-25",
      "2026-07-25",
      "2026-08-25",
      "2026-09-25",
      "2026-10-25",
    ];
    expect(detectRecurrence(on(dates), "2026-10-26")!.nextExpected).toBe(
      "2026-11-25",
    );
  });

  it("counts a bill due on the 1st but paid on the 31st as that month's", () => {
    const dates = [...FIRST.slice(0, 11), "2026-09-30"];
    const verdict = detectRecurrence(on(dates), "2026-10-02")!;
    expect(verdict.nextExpected).toBe("2026-11-01");
  });

  it("still lets a late last payment count from its due date", () => {
    const dates = [...FIRST.slice(0, 11), "2026-10-03"];
    expect(detectRecurrence(on(dates), "2026-10-20")!.nextExpected).toBe(
      "2026-11-01",
    );
  });

  it("does not anchor a drifting every-four-weeks bill", () => {
    const dates = ["2026-06-01", "2026-06-29", "2026-07-27", "2026-08-24"];
    const verdict = detectRecurrence(on(dates), "2026-09-01")!;
    expect(verdict.nextExpected).toBe("2026-09-21");
  });
});

// w21/529: a bill due on the last day of the month is paid on the 30th in a
// 30-day month; counting days as they fell made the 30th the anchor.
describe("a bill due on the last day of the month", () => {
  it("predicts Dec 31 for quarter-ends, seven of them on the 30th", () => {
    const dates = [
      "2023-09-30",
      "2023-12-31",
      "2024-03-31",
      "2024-06-30",
      "2024-09-30",
      "2024-12-31",
      "2025-03-31",
      "2025-06-30",
      "2025-09-30",
      "2025-12-31",
      "2026-03-31",
      "2026-06-30",
      "2026-09-30",
    ];
    const verdict = detectRecurrence(on(dates), "2026-10-22")!;
    expect(verdict.nextExpected).toBe("2026-12-31");
  });

  it("predicts Jul 31 for a monthly series that started on the 30th", () => {
    const dates = [
      "2026-01-31",
      "2026-02-28",
      "2026-03-31",
      "2026-04-30",
      "2026-05-31",
      "2026-06-30",
    ];
    expect(detectRecurrence(on(dates), "2026-06-30")!.nextExpected).toBe(
      "2026-07-31",
    );
  });

  it("still keeps a bill that is really due on the 30th on the 30th", () => {
    const dates = [
      "2026-01-30",
      "2026-02-28",
      "2026-03-30",
      "2026-04-30",
      "2026-05-30",
      "2026-06-30",
    ];
    expect(detectRecurrence(on(dates), "2026-06-30")!.nextExpected).toBe(
      "2026-07-30",
    );
  });
});

describe("a twice-a-month bill paid on the 15th and the last day", () => {
  it("lands on the month's last day", () => {
    const dates = [
      "2026-03-15",
      "2026-03-31",
      "2026-04-15",
      "2026-04-30",
      "2026-05-15",
      "2026-05-31",
      "2026-06-15",
      "2026-06-30",
    ];
    const verdict = detectRecurrence(on(dates), "2026-06-30")!;
    expect(verdict.nextExpected).toBe("2026-07-15");
    const later = detectRecurrence(on([...dates, "2026-07-15"]), "2026-07-15")!;
    expect(later.nextExpected).toBe("2026-07-31");
  });
});
