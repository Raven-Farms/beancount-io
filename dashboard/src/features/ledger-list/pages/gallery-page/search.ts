/** Only text queries belong in the gallery URL; whitespace alone is absent. */
export function validateGallerySearch(search: Record<string, unknown>): {
  q?: string;
} {
  const q = typeof search.q === "string" ? search.q.trim() : "";
  return q ? { q } : {};
}
