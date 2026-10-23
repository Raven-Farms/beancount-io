/**
 * The editor's text size. It is a web view: WKWebView does not apply Dynamic
 * Type to px sizes and the page disables pinch zoom, so ledger source stayed at
 * 14 px at AX2, where native body text is about 33 pt (w21/341). The native side
 * passes `fontScale` and the size follows it, capped. Import-free so the unit
 * runner can load it.
 */
export const EDITOR_BASE_FONT_PX = 14;

/** About iOS's AX2 body scale; the screens' own ceiling (`.pm/DO_NOT_DO.md`). */
export const MAX_EDITOR_FONT_SCALE = 2.4;

/** The code and gutter font size in px for the platform's `fontScale`. */
export function editorFontSize(fontScale: number | undefined): number {
  if (typeof fontScale !== "number" || !Number.isFinite(fontScale)) {
    return EDITOR_BASE_FONT_PX;
  }
  const scale = Math.min(MAX_EDITOR_FONT_SCALE, Math.max(1, fontScale));
  return Math.round(EDITOR_BASE_FONT_PX * scale);
}
