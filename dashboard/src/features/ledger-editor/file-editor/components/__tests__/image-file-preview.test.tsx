import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { GetLedgerFileQuery } from "@/graphql/definitions";
import { imageMimeType } from "@/common/lib/image-mime-type";
import { ImageFileView } from "../non-text-file-views";

vi.mock("../../../shared/components/ledger-file-breadcrumb", () => ({
  default: ({ path }: { path: string }) => <span>{path}</span>,
}));
vi.mock("@/common/hooks/use-is-authenticated", () => ({
  useIsAuthenticated: () => true,
}));
vi.mock("@/common/providers/ledger-provider", () => ({
  useLedger: () => ({
    ledgerData: { permissions: { pull: true, push: true } },
  }),
}));

const file = (
  name: string,
  content: string,
): NonNullable<GetLedgerFileQuery["getLedgerFile"]> => ({
  __typename: "LedgerFileContent",
  name,
  path: name,
  sha: "synthetic",
  size: content.length,
  type: "file",
  encoding: "base64",
  content,
  lastCommitSha: null,
  lastAuthorDate: null,
  lastCommitterDate: null,
});

const view = (name: string, content = "PHN2Zy8+") => (
  <ImageFileView
    key={name}
    filePath={name}
    fileContent={file(name, content)}
    onDelete={vi.fn()}
  />
);

/** Previews use the image MIME type and fall back on a decode error (w4/258). */
describe("ImageFileView", () => {
  it.each([
    ["qa-preview.svg", "image/svg+xml"],
    ["photo.PNG", "image/png"],
    ["scan.jpeg", "image/jpeg"],
    ["anim.gif", "image/gif"],
    ["pic.webp", "image/webp"],
    ["old.bmp", "image/bmp"],
  ])("previews %s as %s", (name, mime) => {
    render(view(name));
    expect(screen.getByRole("img", { name })).toHaveAttribute(
      "src",
      `data:${mime};base64,PHN2Zy8+`,
    );
  });

  it("shows the fallback when the image cannot decode, and retries for another file", () => {
    const { rerender } = render(view("broken.png"));
    fireEvent.error(screen.getByRole("img", { name: "broken.png" }));
    expect(screen.queryByRole("img", { name: "broken.png" })).toBeNull();
    expect(
      screen.getByText("Unable to display image content"),
    ).toBeInTheDocument();

    rerender(view("fine.svg"));
    expect(screen.getByRole("img", { name: "fine.svg" })).toBeInTheDocument();
  });

  it("covers every extension the editor treats as an image", () => {
    for (const ext of ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"]) {
      expect(imageMimeType(`f.${ext}`)).toMatch(/^image\//);
    }
  });
});
