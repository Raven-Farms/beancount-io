import { act, waitFor } from "@testing-library/react";
import { hydrateRoot, type Root } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import { RepositoryListItem } from "../repository-list-item";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  Link: ({
    children,
    className,
  }: {
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href="#ledger" className={className}>
      {children}
    </a>
  ),
}));

/**
 * Real server render, then real hydration with a later clock and another
 * browser zone (w4/m36 t008). 12:30 UTC on 27 July is 28 July in
 * Pacific/Kiritimati (UTC+14).
 */
const originalTz = process.env.TZ;
afterEach(() => {
  vi.useRealTimers();
  process.env.TZ = originalTz;
});

const cards = [
  { name: "qa-first", updatedAt: "2026-07-27T12:17:00.000Z" },
  { name: "qa-second", updatedAt: "2026-07-27T11:00:00.000Z" },
];

function view(list = cards) {
  return (
    <LocalizationProvider localization={createLocalization()}>
      <button type="button">Show more ledgers</button>
      {list.map((card) => (
        <RepositoryListItem
          key={card.name}
          name={card.name}
          fullName={`qa/${card.name}`}
          isPrivate={false}
          updatedAt={card.updatedAt}
          ownerUsername="qa"
        />
      ))}
    </LocalizationProvider>
  );
}

async function serverThenHydrate(
  serverNow: string,
  clientNow: string,
  zone: string,
) {
  vi.useFakeTimers({ toFake: ["Date"] });
  process.env.TZ = "UTC";
  vi.setSystemTime(new Date(serverNow));
  const container = document.createElement("div");
  document.body.appendChild(container);
  container.innerHTML = renderToString(view());
  const times = [...container.querySelectorAll("time")];
  const button = container.querySelector("button")!;
  button.focus();
  const serverTitles = times.map((time) => time.title);

  process.env.TZ = zone;
  vi.setSystemTime(new Date(clientNow));
  const recoverable = vi.fn();
  let root!: Root;
  await act(async () => {
    root = hydrateRoot(container, view(), { onRecoverableError: recoverable });
  });
  return { container, times, button, serverTitles, recoverable, root };
}

const browserTitle = (iso: string) =>
  new Date(iso).toLocaleString("en", {
    dateStyle: "medium",
    timeStyle: "long",
  });

describe("RepositoryListItem hydration", () => {
  it.each([
    // 13 minutes old on the server, 14 on the client.
    [
      "across a relative-age boundary",
      "2026-07-27T12:30:29Z",
      "2026-07-27T12:31:31Z",
    ],
    [
      "within one relative-age window",
      "2026-07-27T12:30:00Z",
      "2026-07-27T12:30:05Z",
    ],
  ])(
    "keeps the cards, their times and focus %s",
    async (_case, serverNow, clientNow) => {
      const h = await serverThenHydrate(serverNow, clientNow, "UTC");

      await waitFor(() => expect(h.times[0]!.textContent).toMatch(/ago$/));
      h.times.forEach((time, i) => {
        expect(time.isConnected).toBe(true);
        expect(time.getAttribute("datetime")).toBe(cards[i]!.updatedAt);
      });
      expect(document.activeElement).toBe(h.button);
      expect(h.recoverable).not.toHaveBeenCalled();
    },
  );

  it("titles initial and newly rendered cards in the browser zone", async () => {
    const h = await serverThenHydrate(
      "2026-07-27T12:30:00Z",
      "2026-07-27T12:30:01Z",
      "Pacific/Kiritimati",
    );

    expect(h.serverTitles[0]).toContain("Jul 27, 2026");
    await waitFor(() => expect(h.times[0]!.title).toContain("Jul 28, 2026"));
    h.times.forEach((time, i) => {
      expect(time.title).toBe(browserTitle(cards[i]!.updatedAt));
    });

    const more = [
      ...cards,
      { name: "qa-third", updatedAt: "2026-07-27T10:30:00.000Z" },
    ];
    await act(async () => h.root.render(view(more)));
    const all = [...h.container.querySelectorAll("time")];
    h.times.forEach((time, i) => expect(all[i]).toBe(time));
    all.forEach((time, i) => {
      expect(time.title).toBe(browserTitle(more[i]!.updatedAt));
      expect(time.getAttribute("datetime")).toBe(more[i]!.updatedAt);
    });
    expect(h.recoverable).not.toHaveBeenCalled();
  });
});
