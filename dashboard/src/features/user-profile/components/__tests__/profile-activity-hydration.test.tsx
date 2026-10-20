import { act, fireEvent, waitFor } from "@testing-library/react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createLocalization } from "@/i18n/init";
import { LocalizationProvider } from "@/i18n/provider";
import type { UserActivityFeedItem } from "@/graphql/definitions";
import { ProfileActivity } from "../profile-activity";

vi.unmock("@/common/hooks/use-translations");
vi.unmock("react-i18next");
vi.mock("@tanstack/react-router", () => ({
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
 * browser zone (w4/m36). 12:30 UTC on 27 July is 28 July in
 * Pacific/Kiritimati (UTC+14).
 */
const originalTz = process.env.TZ;
afterEach(() => {
  vi.useRealTimers();
  process.env.TZ = originalTz;
});

// Six activities, one minute apart, newest at 12:30:00 UTC.
const activities: UserActivityFeedItem[] = Array.from(
  { length: 6 },
  (_, i) => ({
    __typename: "UserActivityFeedItem",
    id: `a${i}`,
    type: "commit_repo",
    content: `Synthetic activity ${i}`,
    createdAt: new Date(Date.UTC(2026, 6, 27, 12, 30 - i)).toISOString(),
    repoFullName: null,
    repoName: null,
  }),
);

function view() {
  return (
    <LocalizationProvider localization={createLocalization()}>
      <ProfileActivity username="qa" activities={activities} />
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
  const showAll = container.querySelector("button")!;
  showAll.focus();
  const serverTitles = times.map((time) => time.title);

  process.env.TZ = zone;
  vi.setSystemTime(new Date(clientNow));
  const recoverable = vi.fn();
  await act(async () => {
    hydrateRoot(container, view(), { onRecoverableError: recoverable });
  });
  return { container, times, showAll, serverTitles, recoverable };
}

const browserTitle = (iso: string) =>
  new Date(iso).toLocaleString("en", {
    dateStyle: "medium",
    timeStyle: "long",
  });

describe("ProfileActivity hydration", () => {
  it.each([
    // Newest is 29s old on the server, 31s on the client.
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
    "keeps the timeline nodes and focus %s",
    async (_case, serverNow, clientNow) => {
      const h = await serverThenHydrate(serverNow, clientNow, "UTC");

      expect(h.times).toHaveLength(5);
      await waitFor(() => expect(h.times[0]!.textContent).toMatch(/ago$/));
      h.times.forEach((time, i) => {
        expect(time.isConnected).toBe(true);
        expect(time.getAttribute("datetime")).toBe(activities[i]!.createdAt);
      });
      expect(document.activeElement).toBe(h.showAll);
      expect(h.recoverable).not.toHaveBeenCalled();
    },
  );

  it("titles initial and expanded rows in the browser zone", async () => {
    const h = await serverThenHydrate(
      "2026-07-28T00:00:00Z",
      "2026-07-28T00:00:01Z",
      "Pacific/Kiritimati",
    );

    expect(h.serverTitles[0]).toContain("Jul 27, 2026");
    await waitFor(() => expect(h.times[0]!.title).toContain("Jul 28, 2026"));
    h.times.forEach((time, i) => {
      expect(time.title).toBe(browserTitle(activities[i]!.createdAt));
    });

    fireEvent.click(h.showAll);
    const all = [...h.container.querySelectorAll("time")];
    expect(all).toHaveLength(6);
    expect(all.slice(0, 5)).toEqual(h.times);
    all.forEach((time, i) => {
      expect(time.title).toBe(browserTitle(activities[i]!.createdAt));
      expect(time.getAttribute("datetime")).toBe(activities[i]!.createdAt);
    });
    expect(h.recoverable).not.toHaveBeenCalled();
  });
});
