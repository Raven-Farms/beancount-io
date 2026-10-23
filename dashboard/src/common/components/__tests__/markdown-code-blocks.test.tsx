import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { MarkdownRenderer } from "../markdown-renderer";

/**
 * A code block keeps its lines and spacing whether or not it names a
 * language; only inline spans render inline (w4/269). Real renderer, real
 * CodeBlock.
 */
const LINES = "qa-20261020 first    aligned\nqa-20261020 second   aligned";
const markdown = [
  "Unlabelled:",
  "",
  "```",
  LINES,
  "```",
  "",
  "Labelled:",
  "",
  "```text",
  LINES,
  "```",
  "",
  "Indented:",
  "",
  ...LINES.split("\n").map((line) => `    ${line}`),
  "",
  "And `inline code` stays inline.",
].join("\n");

describe("Markdown code blocks", () => {
  it("renders every block form as a preformatted block with Copy", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    const { container } = render(<MarkdownRenderer content={markdown} />);

    const blocks = [...container.querySelectorAll("pre")];
    expect(blocks).toHaveLength(3);
    for (const block of blocks) {
      expect(block.textContent).toContain(LINES);
    }
    const inline = screen.getByText("inline code");
    expect(inline.closest("pre")).toBeNull();

    const copies = screen.getAllByRole("button", { name: /copy/i });
    expect(copies).toHaveLength(3);
    // fireEvent: userEvent.setup() would replace this clipboard stub.
    fireEvent.click(copies[0]!);
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(LINES));
    fireEvent.click(copies[2]!);
    await waitFor(() => expect(writeText).toHaveBeenLastCalledWith(LINES));
    expect(
      within(blocks[1]!.parentElement!.parentElement!).getByText("text"),
    ).toBeInTheDocument();
  });
});
