import { useQuery } from "@apollo/client/react";
import { useHydrated } from "@tanstack/react-router";
import { GetLedgerFileDocument } from "@/graphql/definitions";
import { imageMimeType } from "@/common/lib/image-mime-type";

/**
 * An image stored in the ledger, shown from its own bytes through the
 * authorized file read (w4/m37). A Files page URL is HTML, never an image
 * source. Until the bytes arrive — and when the file is missing, denied or
 * not an image — the authored alt text stands in its place. The read waits
 * for hydration, like the README it sits in, so server and client agree.
 */
export function LedgerImage({
  ledgerId,
  path,
  alt,
  title,
}: {
  ledgerId: string;
  path: string;
  alt?: string;
  title?: string;
}) {
  const hydrated = useHydrated();
  const mime = imageMimeType(path);
  const { data } = useQuery(GetLedgerFileDocument, {
    variables: { ledgerId, path },
    fetchPolicy: "cache-first",
    skip: !hydrated || !mime,
  });
  const file = data?.getLedgerFile;

  if (!mime || !file?.content) {
    return (
      <span className="italic text-muted-foreground" title={title}>
        {alt || path}
      </span>
    );
  }
  return (
    <img
      src={`data:${mime};base64,${file.content}`}
      alt={alt ?? ""}
      title={title}
    />
  );
}
