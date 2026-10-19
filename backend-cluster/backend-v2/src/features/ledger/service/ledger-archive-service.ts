import { Readable } from "node:stream";
import type { AppConfig } from "@/config/config";
import type { IModels } from "@/foundation/models";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { Identity } from "@/server/api/identity";
import {
  AUTHORIZATION_ACTIONS,
  type IAuthorizationService,
} from "@/server/api/authorization";
import { getBasicAuthHeader } from "@/features/auth/utils/auth";
import {
  NotFoundError,
  UnauthenticatedError,
  ServiceUnavailableError,
} from "@/shared/errors";
import { parseLedgerId } from "@/shared/str";
import { assertSafeArchiveName } from "../utils/safe-archive-name";
import { authorizeLedger } from "../utils/authorize-ledger";

/**
 * How long Gitea may take to send response headers. It builds the whole
 * archive before its first byte, so this allows for a large one; the deadline
 * is cleared once headers arrive and the body then streams for as long as the
 * caller keeps reading.
 */
export const ARCHIVE_HEADERS_TIMEOUT_MS = 90_000;

export interface ArchiveRequest {
  ledgerId: string;
  archive: string;
  identity?: Identity;
}
/** An authorized archive download, still streaming from Gitea. */
export interface LedgerArchive {
  /** Gitea's body, never buffered here; destroying it ends the Gitea request. */
  body: Readable;
  contentType: string;
  contentDisposition?: string;
  /** Declared byte length, when Gitea sends one. */
  contentLength?: number;
}
export interface ILedgerArchiveService {
  download(args: ArchiveRequest): Promise<LedgerArchive>;
}
/** One authorized Gitea download shared by REST streams and MCP blobs. */
export class LedgerArchiveService implements ILedgerArchiveService {
  constructor(
    private readonly models: Pick<IModels, "user">,
    private readonly db: DbExecutor,
    private readonly config: Pick<AppConfig, "gitea">,
    private readonly authorization: IAuthorizationService,
  ) {}
  async download(args: ArchiveRequest): Promise<LedgerArchive> {
    assertSafeArchiveName(args.archive);
    const { ledgerOwner, ledgerName } = parseLedgerId(args.ledgerId);
    await authorizeLedger(
      args.identity,
      args.ledgerId,
      AUTHORIZATION_ACTIONS.LEDGER_ARCHIVE_READ,
      { authorization: this.authorization },
    );
    // An authorized public read sends no credential, so it cannot reach a
    // private repository even if authorization were wrong.
    let headers: Record<string, string> = {};
    if (args.identity) {
      const user = await this.models.user.getById(
        this.db,
        args.identity.userId,
      );
      if (!user) throw new UnauthenticatedError("User not found");
      headers = getBasicAuthHeader(user.ledger_username, user.ledger_password);
    }
    const controller = new AbortController();
    const deadline = setTimeout(
      () => controller.abort(),
      ARCHIVE_HEADERS_TIMEOUT_MS,
    );
    let response: Response;
    try {
      response = await fetch(
        `${this.config.gitea.internalBaseUrl}/api/v1/repos/${encodeURIComponent(ledgerOwner)}/${encodeURIComponent(ledgerName)}/archive/${encodeURIComponent(args.archive)}`,
        { headers, signal: controller.signal },
      );
    } catch {
      throw new ServiceUnavailableError("Ledger archive");
    } finally {
      clearTimeout(deadline);
    }
    if (!response.ok || !response.body) {
      await response.body?.cancel();
      if (response.status === 404)
        throw new NotFoundError("Archive", args.archive);
      throw new ServiceUnavailableError("Ledger archive");
    }
    const length = response.headers.get("content-length");
    return {
      body: Readable.fromWeb(
        response.body as Parameters<typeof Readable.fromWeb>[0],
      ),
      contentType:
        response.headers.get("content-type") ?? "application/octet-stream",
      contentDisposition:
        response.headers.get("content-disposition") ?? undefined,
      contentLength: length === null ? undefined : Number(length),
    };
  }
}
