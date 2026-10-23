/**
 * What a guest example card says aloud: its title, then what its visible
 * caption says, the description or the reason it is unavailable. The label
 * alone replaced the caption, so an unavailable example gave no reason and an
 * available one skipped its description (w21/243).
 */
export function exampleCardAccessibilityLabel(
  open: string,
  caption: string | null | undefined,
): string {
  return caption ? `${open}, ${caption}` : open;
}
