/**
 * Where a README's authored link or image points inside the ledger, resolved
 * from the README's own folder the way a repository host does (w4/m37):
 * `target.txt` beside `docs/README.md` is `docs/target.txt`, `../main.bean`
 * is `main.bean`. A path ending in `/` names a folder (w4/327): `child/` is
 * `docs/child`, `./` is `docs` and `../` the ledger root (path ""). Returns
 * null for anything that is not repository-relative — a URL with a scheme, a
 * root-relative or fragment-only reference — and for a path that climbs
 * above the ledger root; those keep their authored behavior.
 */
export function resolveReadmeReference(
  reference: string | undefined,
  readmePath: string,
): { path: string; suffix: string; directory: boolean } | null {
  if (
    !reference ||
    /^[a-z][a-z\d+.-]*:/i.test(reference) ||
    /^[/#?]/.test(reference)
  ) {
    return null;
  }
  const cut = reference.search(/[?#]/);
  const authoredPath = cut < 0 ? reference : reference.slice(0, cut);
  const directory = authoredPath.endsWith("/");

  const segments = readmePath.split("/").slice(0, -1);
  for (const raw of authoredPath.split("/")) {
    let segment = raw;
    try {
      segment = decodeURIComponent(raw);
    } catch {
      // Keep a malformed escape as authored.
    }
    if (segment === "" || segment === ".") continue;
    if (segment === "..") {
      if (segments.length === 0) return null;
      segments.pop();
      continue;
    }
    segments.push(segment);
  }
  // Only a folder can be the ledger root.
  if (segments.length === 0 && !directory) return null;
  return {
    path: segments.join("/"),
    suffix: cut < 0 ? "" : reference.slice(cut),
    directory,
  };
}
