/**
 * TanStack's `scrollRestoration`, consulted on every render. On a fresh page
 * the first render after hydration scrolls the window and these containers to
 * the top, but a reader can already have scrolled or tabbed through the server
 * HTML by then, leaving the focused control offscreen (w4/963). That position
 * is the reader's, so only that one restore is skipped when they have moved;
 * every later render — navigation, Back/Forward, a hash — restores as before.
 */
export function respectPreHydrationScroll(containerSelectors: string[]) {
  let firstRender = true;
  return () => {
    if (!firstRender) return true;
    firstRender = false;
    const moved =
      window.scrollX !== 0 ||
      window.scrollY !== 0 ||
      containerSelectors.some((selector) => {
        const container = document.querySelector(selector);
        return (
          container !== null &&
          (container.scrollTop !== 0 || container.scrollLeft !== 0)
        );
      });
    return !moved;
  };
}
