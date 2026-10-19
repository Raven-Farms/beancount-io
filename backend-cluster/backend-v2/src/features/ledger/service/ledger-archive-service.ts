import { Readable } from "node:stream";
import fetch, { type RequestInit, type Response } from "node-fetch";
import type { AppConfig } from "@/config/config";
import type { IModels } from "@/foundation/models";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { Identity } from "@/server/api/identity";
import {
  AUTHORIZATION_ACTIONS,
  type IAuthorizationService,
} from "@/server/api/authorization";
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
export interface ILedgerArchiveService {
  download(args: ArchiveRequest): Promise<Response>;
}
/**
 * One authorized Gitea download shared by REST streams and MCP blobs. The body
 * is Gitea's own stream, never buffered here.
 */
export class LedgerArchiveService implements ILedgerArchiveService {
  constructor(
    private readonly models: Pick<IModels, "user">,
    private readonly db: DbExecutor,
    private readonly config: Pick<AppConfig, "gitea">,
    private readonly authorization: IAuthorizationService,
  ) {}
  async download(args: ArchiveRequest): Promise<Response> {
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
    const headers: Record<string, string> = {};
    if (args.identity) {
      const user = await this.models.user.getById(
        this.db,
        args.identity.userId,
      );
      if (!user) throw new UnauthenticatedError("User not found");
      headers.Authorization = `Basic ${Buffer.from(`${user.ledger_username}:${user.ledger_password}`).toString("base64")}`;
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
        {
          method: "GET",
          headers,
          // @types/node-fetch predates AbortSignal's `reason`; the runtime accepts Node's.
          signal: controller.signal as RequestInit["signal"],
        },
      );
    } catch {
      throw new ServiceUnavailableError("Ledger archive");
    } finally {
      clearTimeout(deadline);
    }
    const body = response.body;
    if (body instanceof Readable) {
      // node-fetch's body is a PassThrough fed by the upstream socket, and
      // destroying it leaves that socket open. A body closed before its end —
      // the caller hung up, or a reader stopped early — therefore aborts the
      // Gitea request itself. node-fetch reports that abort as an `error` on
      // the already-closed body, which may have no reader left to hear it.
      body.on("error", () => {});
      body.once("close", () => {
        if (!body.readableEnded) controller.abort();
      });
    }
    if (!response.ok) {
      if (body instanceof Readable) body.destroy();
      if (response.status === 404)
        throw new NotFoundError("Archive", args.archive);
      throw new ServiceUnavailableError("Ledger archive");
    }
    return response;
  }
}
