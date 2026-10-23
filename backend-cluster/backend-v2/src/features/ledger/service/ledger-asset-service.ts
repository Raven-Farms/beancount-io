import { assertSafeRepoPath } from "@/features/ledger/utils/safe-repo-path";
import { NotFoundError, BadUserInputError } from "@/shared/errors";
import { buildLedgerRepoAssetKey } from "@/features/s3/service/asset-storage-service";
import { parseLedgerId } from "@/shared/str";
import { unwrapFavaResponse } from "@/foundation/fava";
import type { IFavaClientFactory } from "@/foundation/clients/fava-client-factory";
import type { IAssetStorageService } from "@/features/s3/service/asset-storage-service";
import type { AppConfig } from "@/config/config";
import type { Identity } from "@/server/api/identity";
import type { IAuthorizationService } from "@/server/api/authorization";
import {
  authorizeLedger,
  AuthorizedLedgerService,
} from "@/features/ledger/utils/authorize-ledger";
import { AUTHORIZATION_ACTIONS } from "@/server/api/authorization/authorization-contract";

export interface ILedgerAssetService {
  getAssetDownloadUrl(
    ledgerRepoId: number,
    filename: string,
    identity?: Identity,
  ): Promise<string>;
  getLedgerArchiveDownloadUrl(
    ledgerId: string,
    identity?: Identity,
  ): Promise<string>;
}

export class LedgerAssetService
  extends AuthorizedLedgerService
  implements ILedgerAssetService
{
  constructor(
    favaClientFactory: IFavaClientFactory,
    private readonly assetStorage: IAssetStorageService,
    private readonly config: Pick<AppConfig, "oauth">,
    authorization: IAuthorizationService,
  ) {
    super(favaClientFactory, authorization);
  }

  /**
   * Validate that the caller has access to the ledger identified by its stable
   * numeric repoId, then return a presigned S3 download URL for the asset.
   *
   * `ledgerRepoId` has to be resolved to the `owner/name` id `authorizeLedger`
   * expects before the seam can run — that resolution is itself one Fava
   * admin lookup, unavoidable given the two identifiers' different shapes.
   */
  async getAssetDownloadUrl(
    ledgerRepoId: number,
    filename: string,
    identity?: Identity,
  ): Promise<string> {
    if (!Number.isInteger(ledgerRepoId) || ledgerRepoId <= 0) {
      throw new BadUserInputError("Invalid ledgerRepoId");
    }
    assertSafeRepoPath(filename, "filename");
    const adminClient = this.favaClientFactory.getAdminClient();
    const ledger = await unwrapFavaResponse(
      adminClient.admin.getLedgerByRepoId(ledgerRepoId),
      "get ledger",
      () => new NotFoundError("Ledger", String(ledgerRepoId)),
    );

    await authorizeLedger(
      identity,
      ledger.full_name,
      AUTHORIZATION_ACTIONS.LEDGER_FILES_READ,
      this.authDeps,
    );

    const objectKey = buildLedgerRepoAssetKey(ledgerRepoId, filename);
    const { downloadUrl } =
      await this.assetStorage.generateDownloadUrl(objectKey);
    return downloadUrl;
  }

  /**
   * Return a URL that downloads the ledger's `main.zip` archive.
   *
   * An authenticated caller gets the stable v1 URL. Browser navigation sends
   * the HttpOnly session cookie to that endpoint; CLI and API callers send
   * their personal API key or application-API bearer token directly to it.
   * An MCP OAuth token is scoped to the MCP endpoint (ADR 0007) and is refused
   * there. No credential is embedded in the URL.
   *
   * Anonymous callers can only be reading a public ledger (authorizeLedger
   * refuses everything else), so they get the credential-free legacy URL,
   * preserving the existing public archive behavior while the v1 resource
   * surface remains authenticated by default.
   */
  async getLedgerArchiveDownloadUrl(
    ledgerId: string,
    identity?: Identity,
  ): Promise<string> {
    const { ledgerOwner, ledgerName } = parseLedgerId(ledgerId);
    const adminClient = this.favaClientFactory.getAdminClient();
    await unwrapFavaResponse(
      adminClient.ledgers.getLedger(ledgerOwner, ledgerName),
      "get ledger",
      () => new NotFoundError("Ledger", ledgerId),
    );

    await authorizeLedger(
      identity,
      ledgerId,
      AUTHORIZATION_ACTIONS.LEDGER_ARCHIVE_READ,
      this.authDeps,
    );

    // The public origin MCP tokens are minted for, not the backend's own
    // host, so a client sees one host across every URL this server names
    // (w23/023). Production serves the v1 routes under it too.
    const baseUrl = this.config.oauth.issuer.replace(/\/$/, "");

    if (identity?.userId) {
      return `${baseUrl}/api-gateway/v1/ledgers/${encodeURIComponent(ledgerOwner)}/${encodeURIComponent(ledgerName)}/archive/main.zip`;
    }

    // The legacy route addresses the ledger as one `owner%2Fname` segment.
    return `${baseUrl}/api-gateway/ledgers/${encodeURIComponent(ledgerId)}/archive/main.zip`;
  }
}
