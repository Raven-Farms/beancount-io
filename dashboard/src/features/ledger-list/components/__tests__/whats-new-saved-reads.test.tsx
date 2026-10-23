import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FeedSource, type GetChangelogQuery } from "@/graphql/definitions";

/**
 * The real WhatsNew over the real watermark hook: only the changelog read is
 * stubbed, so saved browser data travels the same path as on the dashboard
 * (w4/m39).
 */
type Release = GetChangelogQuery["getFeed"]["items"][number];
const NOW = new Date("2026-10-20T12:00:00.000Z");
const release = (id: string, daysAgo: number): Release => ({
  __typename: "FeedItem",
  id: `changelog:https://beancount.io/blog/${id}`,
  title: `Release ${id}`,
  summary: `Summary ${id}`,
  link: `https://beancount.io/blog/${id}`,
  publishedAt: new Date(NOW.getTime() - daysAgo * 86_400_000).toISOString(),
  source: FeedSource.Changelog,
});
const items = [release("a", 3), release("b", 5)];

vi.mock("@apollo/client/react", () => ({
  useQuery: () => ({
    data: { getFeed: { items, total: items.length, hasMore: false } },
    loading: false,
    error: undefined,
  }),
}));
vi.mock("@/common/analytics/events", () => ({ track: vi.fn() }));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({
    t: (key: string, params?: Record<string, unknown>) =>
      params?.count !== undefined ? `${key}:${params.count}` : key,
    i18n: { language: "en" },
  }),
}));
vi.mock("@/common/hooks/use-date-locale", () => ({
  useFormatRelativeTime: () => () => "3 days ago",
  useDateLocale: () => undefined,
}));

import { WhatsNew } from "../whats-new";

function memoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    getItem: (key) => store.get(key) ?? null,
    setItem: (key, value) => void store.set(key, String(value)),
    removeItem: (key) => void store.delete(key),
    clear: () => store.clear(),
    key: (index) => [...store.keys()][index] ?? null,
    get length() {
      return store.size;
    },
  };
}

const READ_IDS = "beancount.changelog.readIds";
const flags = () =>
  screen.getAllByTestId("release-flag").map((flag) => flag.textContent);

describe("What's new with malformed saved read identities", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(NOW);
    vi.stubGlobal("localStorage", memoryStorage());
    vi.spyOn(console, "warn").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it.each([{}, null, 7, "blog/a"])(
    "renders both releases as new for a saved %j, keeping unrelated keys",
    (value) => {
      localStorage.setItem(READ_IDS, JSON.stringify(value));
      localStorage.setItem("journal.alice/books.showPostings", "true");
      render(<WhatsNew />);

      expect(screen.getByText("common.whatsNewUnread:2")).toBeInTheDocument();
      expect(flags()).toEqual(["!", "!"]);
      expect(localStorage.getItem("journal.alice/books.showPostings")).toBe(
        "true",
      );
    },
  );

  it("survives another tab writing a wrong shape after a valid render", () => {
    localStorage.setItem(READ_IDS, JSON.stringify(["blog/a"]));
    render(<WhatsNew />);
    expect(flags()).toEqual(["*", "!"]);

    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", { key: READ_IDS, newValue: "{}" }),
      );
    });
    expect(flags()).toEqual(["*", "!"]);
    expect(screen.getByText("common.whatsNewUnread:1")).toBeInTheDocument();
  });
});
