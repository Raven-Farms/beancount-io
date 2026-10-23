import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";
import {
  appendCommitPage,
  COMMITS_PAGE_SIZE,
  commitPageOverlaps,
  endRowsFor,
  historyEnded,
  isLastCommitPage,
  shownCommitPages,
} from "../commit-pages";

// w21/313: Recent changes showed only the last 30 commits, with no way to reach
// older history from the app.
const commit = (n: number) => ({ sha: `sha${n}`, message: `commit ${n}` });
const page = (from: number, count: number) =>
  Array.from({ length: count }, (_, i) => commit(from + i));

describe("paging Recent changes", () => {
  it("reaches the oldest commit of a ledger with 45", () => {
    // Page 1 holds the newest 30; page 2 the remaining 15, a short page.
    const first = page(45, 0).concat(page(16, 30).reverse());
    const second = page(1, 15).reverse();
    expect(first.length).toBe(COMMITS_PAGE_SIZE);
    expect(isLastCommitPage(first)).toBe(false);
    expect(isLastCommitPage(second)).toBe(true);
    const all = appendCommitPage(first, second);
    expect(all.length).toBe(45);
    expect(all[all.length - 1]!.sha).toBe("sha1");
  });

  it("lists a commit once when it shifts across pages", () => {
    const shown = [commit(3), commit(2)];
    const older = [commit(2), commit(1)];
    expect(appendCommitPage(shown, older).map((c) => c.sha)).toEqual([
      "sha3",
      "sha2",
      "sha1",
    ]);
  });

  it("a full page is not the last, and an empty one is", () => {
    expect(isLastCommitPage(page(1, COMMITS_PAGE_SIZE))).toBe(false);
    expect(isLastCommitPage([])).toBe(true);
  });
});

// w21/431: a refetch drops the list to its first page; the page counter kept
// beside it stayed at 2 and the next Show older skipped a page.
describe("the page the list is at", () => {
  it("follows the rows shown, not a counter", () => {
    expect(shownCommitPages(0)).toBe(1);
    expect(shownCommitPages(30)).toBe(1);
    expect(shownCommitPages(60)).toBe(2);
    expect(shownCommitPages(46)).toBe(2);
    // A refetch back to page one asks for page two again, not three.
    expect(shownCommitPages(30) + 1).toBe(2);
  });

  it("rounds a list with a shifted duplicate removed up to its page", () => {
    expect(shownCommitPages(59)).toBe(2);
    expect(shownCommitPages(61)).toBe(3);
  });

  it("brings the button back when the list is reset below the last page", () => {
    const source = fs
      .readFileSync(
        path.join(__dirname, "..", "notifications-screen.tsx"),
        "utf8",
      )
      .replace(/\s+/g, "");
    expect(
      source.includes(
        "constnoOlder=historyEnded(shownRows,endRowsFor(historyEnd,headSha));",
      ),
    ).toBe(true);
    expect(source.includes("pagesLoaded")).toBe(false);
  });
});

// w21/498: with 30 or 60 commits the empty page set lastPage to the page asked
// for, but the rows added up to fewer pages, so the button stayed.
describe("the end of the history", () => {
  const source = fs
    .readFileSync(
      path.join(__dirname, "..", "notifications-screen.tsx"),
      "utf8",
    )
    .replace(/\s+/g, "");

  it("an empty page after 30 or 60 commits ends the list", () => {
    for (const count of [30, 60]) {
      const shown = page(1, count);
      const endRows = appendCommitPage(shown, []).length;
      expect(isLastCommitPage([])).toBe(true);
      expect(historyEnded(shown.length, endRows)).toBe(true);
      // A refetch back to the first page brings the button back.
      expect(historyEnded(COMMITS_PAGE_SIZE, endRows)).toBe(count === 30);
    }
    expect(historyEnded(10, null)).toBe(false);
  });

  it("remembers the merged row count, not the page number", () => {
    expect(source.includes("mergedRows=listCommits.length;")).toBe(true);
    expect(source.includes("lastPage")).toBe(false);
    // A refetch back to one page has fewer rows than the end: button returns.
    expect(
      source.includes(
        "noOlder=historyEnded(shownRows,endRowsFor(historyEnd,headSha));",
      ),
    ).toBe(true);
  });
});

// w21/512: an end found before a new commit landed no longer held after the
// foreground refetch, and the oldest commit sat one row past the button.
describe("the end of the history after a new commit", () => {
  it("is forgotten once the newest commit changes", () => {
    const end = { rows: 60, head: "sha-60" };
    expect(endRowsFor(end, "sha-60")).toBe(60);
    expect(endRowsFor(end, "sha-61")).toBe(null);
    expect(endRowsFor(null, "sha-61")).toBe(null);
  });

  it("brings Show older back for the 61-commit ledger", () => {
    const end = { rows: 60, head: "sha-60" };
    // 30 rows shown again, then 60 after Show older: the 61st is still to come.
    expect(historyEnded(60, endRowsFor(end, "sha-61"))).toBe(false);
    // Unchanged history still ends at 60.
    expect(historyEnded(60, endRowsFor(end, "sha-60"))).toBe(true);
  });
});

describe("the Notifications screen's Show older", () => {
  const source = fs
    .readFileSync(
      path.join(__dirname, "..", "notifications-screen.tsx"),
      "utf8",
    )
    .replace(/\s+/g, "");

  it("asks for the next page and merges it", () => {
    expect(source.includes("fetchMoreCommits({variables:{page}")).toBe(true);
    expect(
      source.includes(
        "appendCommitPage(previous.listCommits,fetchMoreResult.listCommits",
      ),
    ).toBe(true);
    expect(
      source.includes(
        "awaitrefetchCommits();}elseif(isLastCommitPage(result.data.listCommits))setHistoryEnd({rows:mergedRows,head:headSha});",
      ),
    ).toBe(true);
  });

  it("shows the button only after a full first page, until a short one", () => {
    expect(
      source.includes(
        "{!commitsPending&&commits.length>=COMMITS_PAGE_SIZE&&!noOlder?(",
      ),
    ).toBe(true);
    expect(en.notificationsShowOlder).toBe("Show older changes");
  });

  it("starts over on a pull to refresh", () => {
    const refresh = source.slice(source.indexOf("constonRefresh="));
    expect(
      refresh
        .slice(0, refresh.indexOf("finally"))
        .includes("setHistoryEnd(null);"),
    ).toBe(true);
  });
});

// w21/626: with 30 or more commits landing while the screen was open, page 2 was
// exactly the rows shown, so Show older asked for it again and again.
describe("a list that moved under Show older", () => {
  it("is told by a page that repeats a shown commit", () => {
    const shown = page(1, 30);
    // 40 new commits: the server's page 2 is the 30 rows already shown.
    expect(commitPageOverlaps(shown, shown)).toBe(true);
    // One new commit shifts page 2 by a row.
    expect(commitPageOverlaps(shown, [commit(30), commit(31)])).toBe(true);
  });

  it("is not told by a page of older commits", () => {
    expect(commitPageOverlaps(page(31, 30), page(1, 30))).toBe(false);
    expect(commitPageOverlaps([], page(1, 3))).toBe(false);
  });
});
