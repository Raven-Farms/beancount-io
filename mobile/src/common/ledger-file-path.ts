/**
 * Whether an error's filename names this ledger file. The server reports
 * repo-relative paths (`2023/transactions.bean`), so those must match the
 * whole path: matching by basename showed `2023/transactions.bean`'s errors
 * on a clean `2024/transactions.bean`, and the root `main.bean`'s on every
 * `sub/main.bean` (w21/089). A leading `./` or `/` is not part of the path.
 * An absolute path, which older engines reported, still matches when it ends
 * in the file's full relative path.
 *
 * Free of `@/` value imports so the jest-lite runner can require it.
 */
export function sameLedgerFile(a: string, b: string): boolean {
  const relative = (file: string) => file.replace(/^(\.\/)+/, "");
  const x = relative(a);
  const y = relative(b);
  if (x.startsWith("/") === y.startsWith("/")) {
    return x.replace(/^\/+/, "") === y.replace(/^\/+/, "");
  }
  const [absolute, rel] = x.startsWith("/") ? [x, y] : [y, x];
  return absolute.endsWith(`/${rel}`);
}
