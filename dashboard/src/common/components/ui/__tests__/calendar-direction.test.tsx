/**
 * DayPicker moves keyboard focus by its `dir` prop, not by the CSS direction
 * it inherits. A Persian (RTL) grid without it sent ArrowLeft to the day drawn
 * on its right (w4/298). These cases press real keys in the real Calendar.
 */
import { cleanup, render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Calendar } from "../calendar";

const app = vi.hoisted(() => ({ language: "fa" }));
vi.mock("@/common/hooks/use-translations", () => ({
  useTranslations: () => ({
    t: (key: string) => key,
    i18n: {
      language: app.language,
      dir: () => (app.language === "fa" ? "rtl" : "ltr"),
    },
  }),
}));

const AUGUST_12 = new Date(2026, 7, 12);
/** DayPicker's `data-day`: the date's `toLocaleDateString()`. */
const dataDay = (day: number) => new Date(2026, 7, day).toLocaleDateString();

function renderCalendar(props: { dir?: string } = {}) {
  const view = render(
    <Calendar
      mode="single"
      selected={AUGUST_12}
      defaultMonth={AUGUST_12}
      onSelect={() => {}}
      {...props}
    />,
  );
  const day = (date: number) =>
    view.container.querySelector<HTMLButtonElement>(
      `button[data-day="${dataDay(date)}"]`,
    )!;
  return { ...view, day };
}

/** The day the arrow key lands on, starting from a focused August 12. */
async function arrowFrom12(
  day: (date: number) => HTMLButtonElement,
  key: "ArrowLeft" | "ArrowRight",
) {
  day(12).focus();
  expect(document.activeElement).toBe(day(12));
  await userEvent.keyboard(`{${key}}`);
  return document.activeElement
    ?.closest("[data-day]")
    ?.getAttribute("data-day");
}

afterEach(() => {
  app.language = "fa";
  cleanup();
});

describe("Calendar keyboard direction", () => {
  it("moves ArrowLeft to the next day in a Persian (RTL) grid", async () => {
    const { container, day } = renderCalendar();
    expect(container.querySelector(".rdp-root")).toHaveAttribute("dir", "rtl");

    expect(await arrowFrom12(day, "ArrowLeft")).toBe(dataDay(13));
    expect(await arrowFrom12(day, "ArrowRight")).toBe(dataDay(11));
  });

  it("keeps ArrowLeft on the previous day in an English (LTR) grid", async () => {
    app.language = "en";
    const { day } = renderCalendar();

    expect(await arrowFrom12(day, "ArrowLeft")).toBe(dataDay(11));
    expect(await arrowFrom12(day, "ArrowRight")).toBe(dataDay(13));
  });

  it("lets an explicit direction override the application's", async () => {
    const { container, day } = renderCalendar({ dir: "ltr" });
    expect(container.querySelector(".rdp-root")).toHaveAttribute("dir", "ltr");
    expect(await arrowFrom12(day, "ArrowLeft")).toBe(dataDay(11));
  });

  it("follows a change of application language", async () => {
    app.language = "en";
    const { day, rerender } = renderCalendar();
    expect(await arrowFrom12(day, "ArrowLeft")).toBe(dataDay(11));

    app.language = "fa";
    rerender(
      <Calendar
        mode="single"
        selected={AUGUST_12}
        defaultMonth={AUGUST_12}
        onSelect={() => {}}
      />,
    );
    expect(await arrowFrom12(day, "ArrowLeft")).toBe(dataDay(13));
  });

  it("keeps vertical keys on the same weekday column", async () => {
    const { day } = renderCalendar();
    day(12).focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(document.activeElement).toBe(day(19));
  });

  it("turns the month chevrons only for a right-to-left grid", () => {
    const rtl = renderCalendar();
    expect(rtl.container.querySelector(".rdp-root")?.className).toMatch(
      /rdp-button\\_previous>svg\]:rotate-180/,
    );
    cleanup();
    const ltr = renderCalendar({ dir: "ltr" });
    expect(ltr.container.querySelector(".rdp-root")?.className).not.toMatch(
      /rotate-180/,
    );
  });
});
