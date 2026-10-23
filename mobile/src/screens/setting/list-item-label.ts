/**
 * What VoiceOver says for a Settings row: the title, then the row's value and
 * description when they are text. An explicit label replaces the children, so
 * the description ("Permanently remove your account and data", "Deleting
 * account…") was never spoken (w21/287). A title that is not text has no label
 * of its own, and the children are read instead.
 */
export function listItemLabel({
  title,
  content,
  description,
}: {
  title: unknown;
  content?: unknown;
  description?: string;
}): string | undefined {
  if (typeof title !== "string") return undefined;
  return [title, typeof content === "string" ? content : "", description ?? ""]
    .filter(Boolean)
    .join(", ");
}
