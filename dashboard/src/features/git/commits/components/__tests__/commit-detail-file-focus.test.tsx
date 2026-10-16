import {
  ApolloClient,
  ApolloLink,
  InMemoryCache,
  Observable,
} from "@apollo/client";
import { ApolloProvider } from "@apollo/client/react";
import {
  act,
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import { CommitDetail } from "../commit-detail";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");

const commit = {
  __typename: "CommitDetails" as const,
  sha: "1234567890abcdef",
  message: "Review removed ledger file",
  author: {
    __typename: "CommitAuthor" as const,
    name: "Ada",
    email: "ada@example.com",
    date: "2026-07-27T12:00:00.000Z",
  },
  committer: null,
  files: [
    { filename: "added.bean", additions: 1, deletions: 0 },
    { filename: "main.bean", additions: 1, deletions: 1 },
    { filename: "deleted.bean", additions: 0, deletions: 1 },
  ].map((file) => ({ __typename: "CommitFileChange" as const, ...file })),
  stats: {
    __typename: "CommitStats" as const,
    additions: 2,
    deletions: 2,
    total: 4,
  },
  parents: [],
  diff: `diff --git a/added.bean b/added.bean
new file mode 100644
index 0000000..1111111
--- /dev/null
+++ b/added.bean
@@ -0,0 +1 @@
+2026-01-01 open Assets:New USD
diff --git a/main.bean b/main.bean
index 1111111..2222222 100644
--- a/main.bean
+++ b/main.bean
@@ -1 +1 @@
-2025-01-01 open Assets:Bank USD
+2026-01-01 open Assets:Bank USD
diff --git a/deleted.bean b/deleted.bean
deleted file mode 100644
index 3333333..0000000
--- a/deleted.bean
+++ /dev/null
@@ -1 +0,0 @@
-2025-01-01 open Assets:Old USD
`,
};

const clients: ApolloClient[] = [];
let scrolls: Array<{
  target: Element;
  options?: boolean | ScrollIntoViewOptions;
}>;

beforeEach(() => {
  window.history.replaceState(
    null,
    "",
    `/ledger/alice/books/commit/${commit.sha}`,
  );
  scrolls = [];
  vi.spyOn(Element.prototype, "scrollIntoView").mockImplementation(function (
    this: Element,
    options?: boolean | ScrollIntoViewOptions,
  ) {
    scrolls.push({ target: this, options });
  });
});

afterEach(() => {
  cleanup();
  clients.splice(0).forEach((client) => client.stop());
  vi.restoreAllMocks();
  window.history.replaceState(null, "", window.location.pathname);
});

async function setup({ hash = "", deferred = false, gated = false } = {}) {
  if (hash)
    window.history.replaceState(null, "", `${window.location.pathname}${hash}`);
  const requests: Array<{ name: string; variables: Record<string, unknown> }> =
    [];
  let deliver = () => {
    throw new Error("Commit query has not started");
  };
  const client = new ApolloClient({
    cache: new InMemoryCache(),
    link: new ApolloLink(
      (operation) =>
        new Observable((observer) => {
          requests.push({
            name: operation.operationName,
            variables: operation.variables,
          });
          if (operation.operationName !== "GetCommitDetails") {
            observer.error(
              new Error(`Unexpected operation: ${operation.operationName}`),
            );
            return;
          }
          deliver = () => {
            observer.next({
              data: {
                getCommitDetails: {
                  ...commit,
                  // Deliberately use reported stats to isolate CommitDetail's load gate;
                  // the real, modest diff still exercises the parser and actual markup.
                  stats: gated
                    ? {
                        ...commit.stats,
                        additions: 800,
                        deletions: 200,
                        total: 1000,
                      }
                    : commit.stats,
                },
              },
            });
            observer.complete();
          };
          if (!deferred) deliver();
        }),
    ),
  });
  clients.push(client);
  const localization = createLocalization();
  render(
    <LocalizationProvider localization={localization}>
      <ApolloProvider client={client}>
        <CommitDetail ledgerId="alice/books" commitSha={commit.sha} />
      </ApolloProvider>
    </LocalizationProvider>,
  );
  await waitFor(() =>
    expect(requests).toEqual([
      {
        name: "GetCommitDetails",
        variables: { ledgerId: "alice/books", sha: commit.sha },
      },
    ]),
  );
  if (!deferred) await screen.findByRole("heading", { name: commit.message });
  return { deliver: () => act(async () => deliver()), requests };
}

function fileSection(filename: string) {
  const section = document.getElementById(`diff-file-${filename}`);
  expect(section, `actual diff section for ${filename}`).not.toBeNull();
  expect(screen.getByTestId("diff-viewer")).toContainElement(section);
  expect(section?.firstElementChild?.textContent).toBe(filename);
  return section!;
}

async function expectScrollTo(section: Element) {
  await waitFor(() =>
    expect(scrolls.some(({ target }) => target === section)).toBe(true),
  );
  const last = scrolls.at(-1)!;
  expect(last.target.id).toBe(section.id);
  expect(last.options).toEqual({ block: "start", behavior: "auto" });
}

async function openFileList() {
  await userEvent.setup().click(screen.getByText("files changed"));
  return screen.getByRole("navigation", { name: "files changed" });
}

describe("CommitDetail file links and real diff sections", () => {
  it("scrolls the deleted file's actual section again when the same-hash link is reactivated", async () => {
    await setup();
    const navigation = await openFileList();
    const link = within(navigation).getByRole("link", {
      name: /^deleted\.bean/,
    });
    expect(link).toHaveAttribute("href", "#diff-file-deleted.bean");
    const user = userEvent.setup();
    // Setting an already-matching URL without hashchange makes both clicks
    // depend on CommitFileList's explicit request, including the second one.
    window.history.replaceState(null, "", "#diff-file-deleted.bean");
    await user.click(link);
    const section = fileSection("deleted.bean");
    expect(section.querySelector(".diff-code-delete")).toHaveTextContent(
      "2025-01-01 open Assets:Old USD",
    );
    await expectScrollTo(section);
    await waitFor(() =>
      expect(window.location.hash).toBe("#diff-file-deleted.bean"),
    );
    const firstCount = scrolls.filter(
      ({ target }) => target === section,
    ).length;
    await user.click(link);
    await waitFor(() =>
      expect(
        scrolls.filter(({ target }) => target === section).length,
      ).toBeGreaterThan(firstCount),
    );
    expect(window.location.hash).toBe("#diff-file-deleted.bean");
    expect(
      scrolls.every(({ target }) => target.id === "diff-file-deleted.bean"),
    ).toBe(true);
  });

  it("retains an initial deleted-file hash while the real commit query is pending", async () => {
    const { deliver } = await setup({
      hash: "#diff-file-deleted.bean",
      deferred: true,
    });
    expect(screen.queryByTestId("diff-viewer")).not.toBeInTheDocument();
    expect(scrolls).toEqual([]);
    await deliver();
    await screen.findByRole("heading", { name: commit.message });
    await expectScrollTo(fileSection("deleted.bean"));
    expect(window.location.hash).toBe("#diff-file-deleted.bean");
  });

  it.each(["initial hash", "file-list link"] as const)(
    "keeps a deleted-file target from the %s until Load Large Diff mounts the real viewer",
    async (source) => {
      await setup({
        gated: true,
        hash: source === "initial hash" ? "#diff-file-deleted.bean" : "",
      });
      expect(screen.queryByTestId("diff-viewer")).not.toBeInTheDocument();
      if (source === "file-list link") {
        const navigation = await openFileList();
        await userEvent
          .setup()
          .click(
            within(navigation).getByRole("link", { name: /^deleted\.bean/ }),
          );
      }
      expect(scrolls).toEqual([]);
      await userEvent
        .setup()
        .click(screen.getByRole("button", { name: "Load Large Diff" }));
      await expectScrollTo(fileSection("deleted.bean"));
      expect(
        screen.queryByRole("button", { name: "Load Large Diff" }),
      ).not.toBeInTheDocument();
    },
  );

  it.each(["added.bean", "main.bean"])(
    "preserves the ordinary %s file link, heading, anchor, and scroll destination",
    async (filename) => {
      await setup();
      const navigation = await openFileList();
      const link = within(navigation).getByRole("link", {
        name: new RegExp(`^${filename.replaceAll(".", "\\.")}`),
      });
      expect(link).toHaveAttribute("href", `#diff-file-${filename}`);
      await userEvent.setup().click(link);
      await expectScrollTo(fileSection(filename));
      expect(
        screen.getByRole("heading", { name: "Changes" }),
      ).toBeInTheDocument();
      expect(screen.getByTestId("commit-metadata")).toHaveTextContent(
        "3 files",
      );
    },
  );
});
