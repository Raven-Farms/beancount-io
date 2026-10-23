/**
 * Whether transaction detail may offer edit/delete header actions.
 * Requires both write permission and ready editable source context, and that
 * the entry is its own source: a copy a plugin generated answers with its
 * source's text and checksum, so Delete would remove the source and every other
 * copy (w21/443).
 */
export function shouldShowTransactionWriteActions(
  canWrite: boolean,
  sha256sum: string | null | undefined,
  isPluginCopy = false,
): boolean {
  return Boolean(canWrite && sha256sum && !isPluginCopy);
}
