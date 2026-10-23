import { act, waitFor } from "@testing-library/react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactElement } from "react";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import { FileUpload } from "../file-upload";
import { ReceiptUploadZone } from "@/features/receipt/components/receipt-upload-zone";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");

/**
 * A server-rendered picker does nothing until hydration attaches its click
 * handler, so it must not look available before then (w4/266). Real SSR
 * markup, real hydration, the real hidden-input click.
 */
afterEach(() => vi.restoreAllMocks());

async function serverThenHydrate(element: ReactElement, chooseLabel: string) {
  const view = (
    <LocalizationProvider localization={createLocalization()}>
      {element}
    </LocalizationProvider>
  );
  const container = document.createElement("div");
  document.body.appendChild(container);
  container.innerHTML = renderToString(view);
  const button = [...container.querySelectorAll("button")].find(
    (candidate) => candidate.textContent === chooseLabel,
  )!;
  const input =
    container.querySelector<HTMLInputElement>('input[type="file"]')!;
  const wrapper = button.closest("[aria-disabled]");

  // Before hydration: honestly unavailable.
  expect(button).toBeDisabled();
  expect(input).toBeDisabled();
  expect(wrapper).toHaveAttribute("aria-disabled", "true");

  const recoverable = vi.fn();
  await act(async () => {
    hydrateRoot(container, view, { onRecoverableError: recoverable });
  });
  await waitFor(() => expect(button).toBeEnabled());
  expect(input).toBeEnabled();
  expect(button.closest("[aria-disabled]")).toBeNull();

  const choose = vi.spyOn(HTMLInputElement.prototype, "click");
  button.click();
  expect(choose.mock.contexts).toEqual([input]);
  expect(recoverable).not.toHaveBeenCalled();
  container.remove();
}

describe("file pickers before and after hydration", () => {
  it("Smart Import Browse files", async () => {
    await serverThenHydrate(<FileUpload />, "Browse files");
  });

  it("Receipt Choose File", async () => {
    await serverThenHydrate(
      <ReceiptUploadZone onFileAccepted={vi.fn()} isUploading={false} />,
      "Choose File",
    );
  });
});
