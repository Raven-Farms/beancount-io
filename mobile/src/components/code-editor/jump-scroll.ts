/**
 * Where to scroll so a line sits in the middle of the part of the editor that
 * is not under the keyboard (w21/340). The editor fills the screen and the
 * keyboard covers its bottom `keyboardInset` px, so centring in the full height
 * put the line behind the accessory bar, or inside the keyboard with the error
 * list open. Import-free so the unit runner can load it.
 *
 * @param lineTop - the line's top within the scrolled content
 * @param clientHeight - the editor's full visible height
 * @param keyboardInset - px of its bottom the keyboard and accessory bar cover
 */
export function jumpScrollTop(
  lineTop: number,
  clientHeight: number,
  keyboardInset: number,
): number {
  const visible = Math.max(0, clientHeight - Math.max(0, keyboardInset));
  return Math.max(0, lineTop - visible / 2);
}
