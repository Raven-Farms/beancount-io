import { useParams } from "@tanstack/react-router";
import { PageSEO } from "@/common/components/seo/page-seo";
import { useFileNavigate } from "@/common/hooks/use-file-navigate";
import { getParentPath } from "../shared/lib/utils";
import { FileNotFoundView } from "./components/ledger-file-view/file-loading-error-views";

/** The blob route's 404: same view as before, never indexed. */
export function FileNotFound() {
  const { ledgerOwner, ledgerName, _splat } = useParams({
    from: "/ledger/$ledgerOwner/$ledgerName/files/blob/$branch/$",
  });
  const fileNavigate = useFileNavigate();
  const filePath = _splat ?? "";

  return (
    <>
      <PageSEO
        titleKey="seo.notFound.title"
        descriptionKey="ledgerEditor.fileNotFound"
        params={{ path: filePath }}
        noIndex
      />
      <FileNotFoundView
        filePath={filePath}
        onBrowseParent={() =>
          fileNavigate(
            `${ledgerOwner}/${ledgerName}`,
            "dir",
            getParentPath(filePath),
          )
        }
      />
    </>
  );
}
