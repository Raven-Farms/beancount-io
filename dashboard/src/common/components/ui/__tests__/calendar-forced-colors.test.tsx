import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Calendar } from "../calendar";

vi.mock("@/common/hooks/use-date-locale", async () => {
  const { enUS } = await import("react-day-picker/locale/en-US");
  return { useDateLocale: () => enUS };
});

/**
 * The committed day's primary fill disappears in forced colors, so picking
 * the 12th or the 13th painted the same calendar (w4/m43). Every day carries
 * `forced-selected` behind the chosen-day attribute, so only the committed
 * day claims the system highlight; its paint was measured in a real browser.
 */
const GATED = "data-[selected-single=true]:forced-selected";

const chosen = (container: HTMLElement) => {
  const days = [
    ...container.querySelectorAll<HTMLButtonElement>("button[data-day]"),
  ];
  for (const day of days) expect(day).toHaveClass(GATED);
  return days
    .filter((day) => day.dataset.selectedSingle === "true")
    .map((day) => day.textContent);
};

describe("Calendar's selected day under forced colors", () => {
  it("gates the highlight on exactly the committed day, which follows a new choice", () => {
    const month = new Date(2016, 7, 1);
    const { container, rerender } = render(
      <Calendar
        mode="single"
        onSelect={() => {}}
        defaultMonth={month}
        selected={new Date(2016, 7, 12)}
      />,
    );
    expect(chosen(container)).toEqual(["12"]);

    rerender(
      <Calendar
        mode="single"
        onSelect={() => {}}
        defaultMonth={month}
        selected={new Date(2016, 7, 13)}
      />,
    );
    expect(chosen(container)).toEqual(["13"]);
  });

  it("leaves range days to their own treatment", () => {
    const { container } = render(
      <Calendar
        mode="range"
        defaultMonth={new Date(2016, 7, 1)}
        selected={{ from: new Date(2016, 7, 12), to: new Date(2016, 7, 14) }}
      />,
    );
    expect(chosen(container)).toEqual([]);
  });
});
