import { formatCommitAuthorLine } from "../formatting";

// Midday UTC, so the calendar day is the same in every time zone the runner uses.
const SEPT_13 = "2026-09-13T12:00:00Z";

// Newer ICU puts a narrow no-break space before AM/PM; the tests read it as one.
const plain = (text: string) => text.replace(/\u202f/g, " ");

describe("formatCommitAuthorLine", () => {
  it("adds the day a commit was made to its author", () => {
    expect(
      plain(formatCommitAuthorLine("Dora Noda", SEPT_13, "en", "UTC")),
    ).toBe("Dora Noda · Sep 13, 2026, 12:00 PM");
  });

  it("shows the author alone when the date is missing or unparseable", () => {
    for (const date of [undefined, null, "", "not a date"]) {
      expect(formatCommitAuthorLine("Tian Pan", date, "en")).toBe("Tian Pan");
    }
  });

  it("tells apart two commits by the same author with the same message", () => {
    const earlier = formatCommitAuthorLine(
      "Tian Pan",
      "2026-09-10T12:00:00Z",
      "en",
    );
    const later = formatCommitAuthorLine(
      "Tian Pan",
      "2026-09-12T12:00:00Z",
      "en",
    );
    expect(earlier === later).toBe(false);
  });

  it("formats the date in the app language", () => {
    const english = formatCommitAuthorLine("Dora Noda", SEPT_13, "en");
    const german = formatCommitAuthorLine("Dora Noda", SEPT_13, "de");
    expect(german === english).toBe(false);
    expect(german.startsWith("Dora Noda · ")).toBe(true);
    expect(german.includes("2026")).toBe(true);
  });
});

// w21/487: same-day commits differed only by their SHA.
describe("formatCommitAuthorLine and the time of day", () => {
  it("shows when in the day, so two commits of one day read differently", () => {
    const morning = formatCommitAuthorLine(
      "puncsky",
      "2026-10-21T09:05:00Z",
      "en",
      "UTC",
    );
    const afternoon = formatCommitAuthorLine(
      "puncsky",
      "2026-10-21T17:40:00Z",
      "en",
      "UTC",
    );
    expect(plain(morning)).toBe("puncsky · Oct 21, 2026, 9:05 AM");
    expect(plain(afternoon)).toBe("puncsky · Oct 21, 2026, 5:40 PM");
    expect(morning === afternoon).toBe(false);
  });

  it("is read in the zone asked for", () => {
    expect(
      plain(
        formatCommitAuthorLine(
          "puncsky",
          "2026-10-21T17:40:00Z",
          "en",
          "America/Los_Angeles",
        ),
      ),
    ).toBe("puncsky · Oct 21, 2026, 10:40 AM");
  });

  it("keeps the author alone for an unparseable time", () => {
    expect(formatCommitAuthorLine("puncsky", "yesterday", "en", "UTC")).toBe(
      "puncsky",
    );
  });
});
