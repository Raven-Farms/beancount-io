import { afterEach, describe, expect, it } from "vitest";
import { respectPreHydrationScroll } from "../respect-pre-hydration-scroll";

const PANE = '[data-scroll-restoration-id="ledger-content"]';

function scrollWindowTo(x: number, y: number) {
  Object.defineProperty(window, "scrollX", { configurable: true, value: x });
  Object.defineProperty(window, "scrollY", { configurable: true, value: y });
}

afterEach(() => {
  scrollWindowTo(0, 0);
  document.body.innerHTML = "";
});

/** Only the first restore yields to a reader who already moved (w4/963). */
describe("respectPreHydrationScroll", () => {
  it("restores an untouched fresh page, and every render after it", () => {
    const shouldRestore = respectPreHydrationScroll([PANE]);
    expect(shouldRestore()).toBe(true);
    scrollWindowTo(0, 1313);
    expect(shouldRestore()).toBe(true);
  });

  it("keeps the window where the reader tabbed or scrolled before hydration", () => {
    const shouldRestore = respectPreHydrationScroll([PANE]);
    scrollWindowTo(0, 1313);
    expect(shouldRestore()).toBe(false);
    // Navigation, Back/Forward and hashes restore as before.
    expect(shouldRestore()).toBe(true);
    expect(shouldRestore()).toBe(true);
  });

  it("keeps the ledger pane where the reader moved it before hydration", () => {
    document.body.innerHTML = `<main data-scroll-restoration-id="ledger-content"></main>`;
    const pane = document.querySelector(PANE)!;
    pane.scrollTop = 420;
    const shouldRestore = respectPreHydrationScroll([PANE]);
    expect(shouldRestore()).toBe(false);
    expect(shouldRestore()).toBe(true);
  });

  it("restores when a listed pane is absent or at its origin", () => {
    document.body.innerHTML = `<main data-scroll-restoration-id="ledger-content"></main>`;
    expect(respectPreHydrationScroll([PANE])()).toBe(true);
    document.body.innerHTML = "";
    expect(respectPreHydrationScroll([PANE])()).toBe(true);
  });
});
