import fs from "fs";
import path from "path";
import { en } from "../../../translations/en";
import {
  appendCommitPage,
  COMMITS_PAGE_SIZE,
  isLastCommitPage,
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

describe("the Notifications screen's Show older", () => {
  const source = fs
    .readFileSync(
      path.join(__dirname, "..", "notifications-screen.tsx"),
      "utf8",
    )
    .replace(/\s+/g, "");

  it("asks for the next page and merges it", () => {
    expect(
      source.includes("fetchMoreCommits({variables:{page:pagesLoaded+1}"),
    ).toBe(true);
    expect(
      source.includes(
        "appendCommitPage(previous.listCommits,fetchMoreResult.listCommits",
      ),
    ).toBe(true);
    expect(
      source.includes(
        "if(isLastCommitPage(result.data.listCommits))setNoOlder(true);",
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
        .includes("setPagesLoaded(1);setNoOlder(false);"),
    ).toBe(true);
  });
});
