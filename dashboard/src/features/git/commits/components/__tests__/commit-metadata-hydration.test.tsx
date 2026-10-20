import { act, waitFor } from "@testing-library/react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import { CommitMetadata } from "../commit-metadata";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");

/**
 * Real server render, then real hydration with a later clock and another
 * browser zone (w4/m36). Pacific/Kiritimati is UTC+14, so 12:30 UTC on
 * 27 July is already 28 July there.
 */
const authorDate = "2026-07-27T12:30:00.000Z";
const originalTz = process.env.TZ;

afterEach(() => {
  vi.useRealTimers();
  process.env.TZ = originalTz;
});

function view() {
  return (
    <LocalizationProvider localization={createLocalization()}>
      <CommitMetadata
        sha="1234567890abcdef"
        message="Synthetic commit"
        author={{ name: "Ada", email: "ada@example.com", date: authorDate }}
        fileCount={1}
        stats={{ additions: 1, deletions: 0, total: 1 }}
      />
    </LocalizationProvider>
  );
}

async function serverThenHydrate(
  serverNow: string,
  clientNow: string,
  clientZone: string,
) {
  vi.useFakeTimers({ toFake: ["Date"] });
  process.env.TZ = "UTC";
  vi.setSystemTime(new Date(serverNow));
  const container = document.createElement("div");
  document.body.appendChild(container);
  container.innerHTML = renderToString(view());
  const time = container.querySelector("time")!;
  const copy = container.querySelector("button")!;
  copy.focus();
  const serverText = time.textContent;
  const serverLabel = time.getAttribute("aria-label");

  process.env.TZ = clientZone;
  vi.setSystemTime(new Date(clientNow));
  const recoverable = vi.fn();
  await act(async () => {
    hydrateRoot(container, view(), { onRecoverableError: recoverable });
  });
  return { container, time, copy, serverText, serverLabel, recoverable };
}

describe("CommitMetadata hydration", () => {
  it.each([
    // 29s old on the server, 31s on the client: "less than a minute" → "1 minute".
    [
      "across a relative-age boundary",
      "2026-07-27T12:30:29Z",
      "2026-07-27T12:30:31Z",
    ],
    [
      "within one relative-age window",
      "2026-07-27T15:00:00Z",
      "2026-07-27T15:00:05Z",
    ],
  ])(
    "keeps the time node and focus %s",
    async (_case, serverNow, clientNow) => {
      const h = await serverThenHydrate(serverNow, clientNow, "UTC");

      expect(h.serverText).toContain("Jul 27, 2026");
      await waitFor(() => expect(h.time.textContent).toMatch(/ago$/));
      expect(h.container.querySelector("time")).toBe(h.time);
      expect(document.activeElement).toBe(h.copy);
      expect(h.copy.isConnected).toBe(true);
      expect(h.time.getAttribute("datetime")).toBe(authorDate);
      expect(h.recoverable).not.toHaveBeenCalled();
    },
  );

  it("names the exact time in the browser zone after hydration", async () => {
    const h = await serverThenHydrate(
      "2026-07-28T00:00:00Z",
      "2026-07-28T00:00:01Z",
      "Pacific/Kiritimati",
    );

    expect(h.serverLabel).toContain("Jul 27, 2026");
    expect(h.serverLabel).toContain("UTC");
    await waitFor(() =>
      expect(h.time.getAttribute("aria-label")).toContain("Jul 28, 2026"),
    );
    expect(h.time.getAttribute("aria-label")).toBe(
      new Intl.DateTimeFormat("en", {
        dateStyle: "medium",
        timeStyle: "long",
      }).format(new Date(authorDate)),
    );
    expect(h.container.querySelector("time")).toBe(h.time);
    expect(h.time.getAttribute("datetime")).toBe(authorDate);
    expect(h.recoverable).not.toHaveBeenCalled();
  });
});
