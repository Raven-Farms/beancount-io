import fs from "fs";
import path from "path";
import { commitRowAccessibilityLabel } from "../formatting";

// w21/224: a label on a pressable replaces its children, so VoiceOver read
// only the subject and five commits with one subject sounded identical.
describe("commitRowAccessibilityLabel", () => {
  const commit = (sha: string, day: string) => ({
    subject: "qa: mobile remove/append",
    sha,
    shortSha: sha.slice(0, 7),
    author: { name: "QA Bot", date: `${day}T12:00:00Z` },
  });

  it("reads the subject, then the author and day, then the short SHA", () => {
    expect(
      commitRowAccessibilityLabel(
        commit("0530ce7aaaaaaaa", "2026-10-21"),
        "(no message)",
        "en",
      ),
    ).toBe("qa: mobile remove/append, QA Bot · Oct 21, 2026, 0530ce7");
  });

  it("tells commits with one subject apart", () => {
    const labels = [
      commitRowAccessibilityLabel(commit("aaaaaaa1", "2026-10-20"), "-", "en"),
      commitRowAccessibilityLabel(commit("bbbbbbb2", "2026-10-20"), "-", "en"),
      commitRowAccessibilityLabel(commit("ccccccc3", "2026-10-21"), "-", "en"),
    ];
    expect(new Set(labels).size).toBe(3);
  });

  it("uses the server's short SHA when it sends one, and the author alone without a date", () => {
    expect(
      commitRowAccessibilityLabel(
        {
          subject: "Fix",
          sha: "0123456789",
          shortSha: "01234",
          author: { name: "Ann" },
        },
        "-",
        "en",
      ),
    ).toBe("Fix, Ann, 01234");
  });

  it("names a commit with an empty message instead of leaving the row blank", () => {
    expect(
      commitRowAccessibilityLabel(
        { ...commit("dddddddd", "2026-10-21"), subject: "" },
        "(no message)",
        "en",
      ).startsWith("(no message), QA Bot"),
    ).toBe(true);
  });

  it("is what the Notifications row announces and shows", () => {
    const source = fs
      .readFileSync(
        path.join(__dirname, "..", "notifications-screen.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(
      source.includes(
        'accessibilityLabel={commitRowAccessibilityLabel(commit,t("commitNoMessage"),locale,)}',
      ),
    ).toBe(true);
    expect(source.includes('{commit.subject||t("commitNoMessage")}')).toBe(
      true,
    );
  });
});
