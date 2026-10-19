import type { RouterContext } from "@koa/router";
import type { AppLayers } from "@/foundation/composition";
import type { ArchiveRequest } from "../../service/ledger-archive-service";

/** Both REST spellings stream the same protected archive download. */
export async function streamLedgerArchive(
  ctx: RouterContext,
  layers: AppLayers,
  args: ArchiveRequest,
): Promise<void> {
  const archive = await layers.services.ledgerArchive.download(args);
  ctx.set("content-type", archive.contentType);
  if (archive.contentDisposition)
    ctx.set("content-disposition", archive.contentDisposition);
  ctx.set("Cache-Control", "private, no-store");
  ctx.body = archive.body;
}
