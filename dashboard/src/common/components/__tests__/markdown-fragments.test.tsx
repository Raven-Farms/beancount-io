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
