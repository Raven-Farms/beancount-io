import { MockedProvider } from "@apollo/client/testing/react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { describe, expect, it, vi } from "vitest";
import { GetLedgerFileDocument } from "@/graphql/definitions";
import { resolveReadmeReference } from "@/common/lib/readme-reference";
import { MarkdownRenderer } from "../markdown-renderer";

/** A README's relative links and images resolve from its folder (w4/m37). */
describe("resolveReadmeReference", () => {
  it.each([
    ["target.txt", "docs/README.md", "docs/target.txt", ""],
    ["../main.bean", "docs/README.md", "main.bean", ""],
    ["./img/chart.png", "docs/README.md", "docs/img/chart.png", ""],
    ["main.bean", "README.md", "main.bean", ""],
    ["a%20b.txt#L3", "docs/README.md", "docs/a b.txt", "#L3"],
    ["notes.md?plain=1", "docs/README.md", "docs/notes.md", "?plain=1"],
  ])("resolves %s from %s", (reference, readme, path, suffix) => {
    expect(resolveReadmeReference(reference, readme)).toEqual({
      path,
      suffix,
      directory: false,
    });
  });

  // A trailing slash names a folder, resolved from the README's (w4/327).
  it.each([
    ["receipts/", "docs/README.md", "docs/receipts", ""],
    ["./", "docs/README.md", "docs", ""],
    ["../", "docs/README.md", "", ""],
    ["../accounts/", "docs/README.md", "accounts", ""],
    ["./", "README.md", "", ""],
    ["receipts/?view=list", "docs/README.md", "docs/receipts", "?view=list"],
  ])("resolves folder %s from %s", (reference, readme, path, suffix) => {
    expect(resolveReadmeReference(reference, readme)).toEqual({
      path,
      suffix,
      directory: true,
    });
  });

  it.each([
    "https://example.com/x",
    "mailto:qa@example.com",
    "/ledger/qa/books/files/blob/main/main.bean",
    "#section",
    "../../outside.txt",
    "../../outside/",
    "",
  ])("leaves %s as authored", (reference) => {
    expect(resolveReadmeReference(reference, "docs/README.md")).toBeNull();
  });
});

const ledgerId = "qa/books";
const source = { ledgerId, path: "docs/README.md" };
const markdown = [
  "[target](target.txt) [main](../main.bean) [spaced](a%20b.txt#L3)",
  "[folder](receipts/) [here](./) [up](../)",
  "[site](https://example.com/x) [root](/ledger/qa/books/journal) [top](#top)",
  "",
  "![Flow chart](img/chart.png)",
  "![Remote](https://example.com/logo.png)",
].join("\n");

// 1×1 transparent PNG.
const pngBase64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";
const fileResult = (content: string | null) => ({
  getLedgerFile: {
    __typename: "LedgerFile",
    name: "chart.png",
    path: "docs/img/chart.png",
    sha: "s",
    size: 68,
    type: "file",
    encoding: "base64",
    content,
    lastCommitSha: null,
    lastAuthorDate: null,
    lastCommitterDate: null,
  },
});
const imageMock = (content: string | null) => ({
  request: {
    query: GetLedgerFileDocument,
    variables: { ledgerId, path: "docs/img/chart.png" },
  },
  result: { data: fileResult(content) },
});

describe("MarkdownRenderer with a README source", () => {
  it("renders native file hrefs that the file route reads back exactly", () => {
    render(
      <MockedProvider mocks={[imageMock(pngBase64)]}>
        <MarkdownRenderer content={markdown} source={source} />
      </MockedProvider>,
    );
    const href = (name: string) =>
      screen.getByRole("link", { name }).getAttribute("href");
    expect(href("target")).toBe(
      "/ledger/qa/books/files/blob/main/docs/target.txt",
    );
    expect(href("main")).toBe("/ledger/qa/books/files/blob/main/main.bean");
    expect(href("spaced")).toBe(
      "/ledger/qa/books/files/blob/main/docs/a%20b.txt#L3",
    );
    expect(href("folder")).toBe(
      "/ledger/qa/books/files/tree/main/docs/receipts",
    );
    expect(href("here")).toBe("/ledger/qa/books/files/tree/main/docs");
    expect(href("up")).toBe("/ledger/qa/books/files/tree/main");
    expect(href("site")).toBe("https://example.com/x");
    expect(href("root")).toBe("/ledger/qa/books/journal");
    expect(href("top")).toBe("#top");

    const root = createRootRoute();
    const blob = createRoute({
      getParentRoute: () => root,
      path: "/ledger/$ledgerOwner/$ledgerName/files/blob/$branch/$",
    });
    const tree = createRoute({
      getParentRoute: () => root,
      path: "/ledger/$ledgerOwner/$ledgerName/files/tree/$branch/$",
    });
    const router = createRouter({
      routeTree: root.addChildren([blob, tree]),
      history: createMemoryHistory(),
    });
    for (const [name, path] of [
      ["target", "docs/target.txt"],
      ["main", "main.bean"],
      ["spaced", "docs/a b.txt"],
      ["folder", "docs/receipts"],
      ["here", "docs"],
    ] as const) {
      const match = router.matchRoutes(
        new URL(href(name)!, "http://x").pathname,
      );
      expect(match.at(-1)?.params).toMatchObject({
        ledgerOwner: "qa",
        ledgerName: "books",
        branch: "main",
        _splat: path,
      });
    }
  });

  it("shows a relative image from its ledger bytes and keeps absolute ones", async () => {
    render(
      <MockedProvider mocks={[imageMock(pngBase64)]}>
        <MarkdownRenderer content={markdown} source={source} />
      </MockedProvider>,
    );
    const image = await screen.findByRole("img", { name: "Flow chart" });
    expect(image).toHaveAttribute("src", `data:image/png;base64,${pngBase64}`);
    expect(screen.getByRole("img", { name: "Remote" })).toHaveAttribute(
      "src",
      "https://example.com/logo.png",
    );
  });

  it("keeps the alt text when the image cannot be read", async () => {
    render(
      <MockedProvider
        mocks={[
          {
            request: imageMock(null).request,
            error: new Error("denied"),
          },
        ]}
      >
        <MarkdownRenderer content={markdown} source={source} />
      </MockedProvider>,
    );
    await act(async () => {});
    expect(screen.getByText("Flow chart")).toBeInTheDocument();
    expect(
      screen.queryByRole("img", { name: "Flow chart" }),
    ).not.toBeInTheDocument();
  });

  it("hydrates server markup with the same hrefs and image placeholder", async () => {
    const view = (
      <MockedProvider mocks={[imageMock(pngBase64)]}>
        <MarkdownRenderer content={markdown} source={source} />
      </MockedProvider>
    );
    const container = document.createElement("div");
    document.body.appendChild(container);
    container.innerHTML = renderToString(view);
    const link = container.querySelector('a[href$="docs/target.txt"]');
    expect(link).not.toBeNull();
    expect(container.textContent).toContain("Flow chart");

    const recoverable = vi.fn();
    let root: ReturnType<typeof hydrateRoot> | undefined;
    await act(async () => {
      root = hydrateRoot(container, view, { onRecoverableError: recoverable });
    });
    await waitFor(() =>
      expect(container.querySelector("img[alt='Flow chart']")).not.toBeNull(),
    );
    expect(container.querySelector('a[href$="docs/target.txt"]')).toBe(link);
    expect(recoverable).not.toHaveBeenCalled();
    act(() => root?.unmount());
    container.remove();
  });

  it("leaves Markdown without a source unchanged", () => {
    render(<MarkdownRenderer content={markdown} />);
    expect(screen.getByRole("link", { name: "target" })).toHaveAttribute(
      "href",
      "target.txt",
    );
    expect(screen.getByRole("img", { name: "Flow chart" })).toHaveAttribute(
      "src",
      "img/chart.png",
    );
  });
});
