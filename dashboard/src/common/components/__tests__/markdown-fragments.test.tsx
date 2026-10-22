import { render, screen } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MarkdownRenderer } from "../markdown-renderer";

/** Fragment links reach sanitized authored ids (w4/282). */
const README = [
  "[qa-20261020 authored jump](#qa-20261020-fragment-target)",
  "",
  "[qa-20261020 renderer-prefix control](#user-content-qa-20261020-fragment-target)",
  "",
  "[qa missing](#qa-20261020-nowhere)",
  "",
  "[qa malformed](#%E0%A4%A)",
  "",
  "[qa encoded](#caf%C3%A9)",
  "",
  "[qa external](https://example.com/#qa-20261020-fragment-target)",
  "",
  '<h2 id="qa-20261020-fragment-target">qa-20261020 destination</h2>',
  "",
  '<h3 id="café">qa encoded destination</h3>',
  "",
  '<script id="qa-script">alert(1)</script>',
].join("\n");

const href = (name: string) =>
  screen.getByRole("link", { name }).getAttribute("href")!;
const targetOf = (name: string) =>
  document.getElementById(decodeURIComponent(href(name).slice(1)));

describe.each([
  ["Markdown", {}],
  ["a README", { source: { ledgerId: "o/l", path: "qa/README.md" } }],
])("fragment links in %s", (_, props) => {
  it("reach the sanitized authored id, keeping the clobber prefix", () => {
    render(<MarkdownRenderer content={README} {...props} />);
    const destination = screen.getByRole("heading", {
      name: "qa-20261020 destination",
    });

    expect(destination.id).toBe("user-content-qa-20261020-fragment-target");
    expect(document.getElementById("qa-20261020-fragment-target")).toBeNull();
    expect(targetOf("qa-20261020 authored jump")).toBe(destination);
    expect(href("qa-20261020 renderer-prefix control")).toBe(
      "#user-content-qa-20261020-fragment-target",
    );
    expect(targetOf("qa-20261020 renderer-prefix control")).toBe(destination);
    expect(targetOf("qa encoded")).toBe(
      screen.getByRole("heading", { name: "qa encoded destination" }),
    );
  });

  it("leaves missing, malformed and external fragments as authored", () => {
    const { container } = render(
      <MarkdownRenderer content={README} {...props} />,
    );

    expect(href("qa missing")).toBe("#qa-20261020-nowhere");
    // Markdown escapes the stray `%`; the result still does not decode.
    expect(href("qa malformed")).toBe("#%E0%A4%25A");
    expect(href("qa external")).toBe(
      "https://example.com/#qa-20261020-fragment-target",
    );
    expect(container.querySelector("script")).toBeNull();
  });
});

it("renders the same fragment href on the server", () => {
  expect(renderToString(<MarkdownRenderer content={README} />)).toContain(
    'href="#user-content-qa-20261020-fragment-target"',
  );
});

/**
 * The code overrides rebuilt their elements and dropped the sanitized id and
 * the authored direction: a link to a code block reached nothing, and
 * `dir="ltr"` code read "8 = 2 − 10" in a Persian page (w4/303).
 */
describe("code anchors and authored direction", () => {
  const CODE_README = [
    "[qa code anchor](#qa-code-target)",
    "",
    "[qa inline anchor](#user-content-qa-inline-target)",
    "",
    "[qa heading anchor](#qa-heading-target)",
    "",
    '<pre id="qa-code-target" dir="ltr"><code>qa code',
    "    10 - 2 = 8",
    "    aligned line</code></pre>",
    "",
    '<p><code id="qa-inline-target" dir="ltr">qa inline</code></p>',
    "",
    '<h2 id="qa-heading-target">qa heading control</h2>',
    "",
    '<pre dir="sideways"><code>qa odd direction</code></pre>',
    "",
    "```",
    "qa plain fence",
    "```",
  ].join("\n");

  it("links reach code blocks and inline code by their sanitized ids", () => {
    render(<MarkdownRenderer content={CODE_README} />);
    const block = targetOf("qa code anchor");
    expect(block?.tagName).toBe("PRE");
    expect(block).toHaveAttribute("id", "user-content-qa-code-target");
    expect(block?.textContent).toContain("    10 - 2 = 8");
    const inline = targetOf("qa inline anchor");
    expect(inline?.tagName).toBe("CODE");
    expect(inline).toHaveTextContent("qa inline");
    expect(targetOf("qa heading anchor")?.tagName).toBe("H2");
    // The clobber prefix stays: no unprefixed id reaches the document.
    expect(document.getElementById("qa-code-target")).toBeNull();
    expect(document.getElementById("qa-inline-target")).toBeNull();
  });

  it("keeps an allowed authored direction and adds none otherwise", () => {
    const { container } = render(<MarkdownRenderer content={CODE_README} />);
    const pres = [...container.querySelectorAll("pre")];
    const byText = (text: string) =>
      pres.find((pre) => pre.textContent?.includes(text));
    expect(byText("10 - 2 = 8")).toHaveAttribute("dir", "ltr");
    expect(
      document.getElementById("user-content-qa-inline-target"),
    ).toHaveAttribute("dir", "ltr");
    expect(byText("qa odd direction")).not.toHaveAttribute("dir");
    expect(byText("qa plain fence")).not.toHaveAttribute("dir");
    expect(byText("qa plain fence")).not.toHaveAttribute("id");
  });

  it("renders the same ids and direction on the server", () => {
    const html = renderToString(<MarkdownRenderer content={CODE_README} />);
    expect(html).toMatch(
      /<pre[^>]*id="user-content-qa-code-target"[^>]*dir="ltr"|<pre[^>]*dir="ltr"[^>]*id="user-content-qa-code-target"/,
    );
    expect(html).toContain('id="user-content-qa-inline-target"');
  });
});
