import { notFound } from "@tanstack/react-router";

/** The only branch the Files routes read, list and write. */
export const SUPPORTED_BRANCH = "main";

/**
 * Called from `beforeLoad` of the `files/{blob,tree,new,upload}/$branch` routes: any other
 * branch is a 404, never main's content (or a write to main) under a URL that
 * names a branch it does not show (w4/281).
 */
export function requireSupportedBranch(branch: string): void {
  if (branch !== SUPPORTED_BRANCH) throw notFound();
}
