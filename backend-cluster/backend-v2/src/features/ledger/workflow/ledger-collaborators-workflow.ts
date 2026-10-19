import { type IStripeService } from "@/features/stripe/service/stripe-service";
import { type IFavaClientFactory } from "@/foundation/clients/fava-client-factory";
import {
  getTierLimits,
  TIER_DISPLAY_NAMES,
} from "@/features/stripe/service/stripe";
import { getUserTier } from "@/features/stripe/operations/get-user-tier";
import { parseLedgerId } from "@/shared/str";
import {
  BadUserInputError,
  InternalServerError,
  ResourceLimitReachedError,
} from "@/shared/errors";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { IModels } from "@/foundation/models";
import { readGiteaPages } from "@/shared/gitea-pages";
import { UserPublic, unwrapFavaResponse } from "@/foundation/fava";
import { logger } from "@/shared/logger";
import type { Identity } from "@/server/api/identity";
import {
  AUTHORIZATION_ACTIONS,
  ledgerResource,
  type IAuthorizationService,
} from "@/server/api/authorization";

const moduleLogger = logger.child({ module: "ledger-collaborators-workflow" });

/**
 * Gitea reports an unknown username as "user does not exist
 * [uid: 0, name: …]" — an internal shape no agent can act on. The
 * collaborator name came from the caller, so this is their input error.
 * Anything else is returned unchanged for the caller to rethrow.
 */
function translateUnknownUser(error: unknown, collaborator: string): unknown {
  const message = error instanceof Error ? error.message : String(error);
  return /user does not exist/i.test(message)
    ? new BadUserInputError(`No such user: ${collaborator}`)
    : error;
}

/**
 * A blank collaborator name is refused here rather than only in the adapters'
 * schemas, because GraphQL hands its string argument over unvalidated. Sent
 * upstream it fails opaquely and reads as a server fault.
 */
function assertCollaboratorName(collaborator: string): void {
  if (collaborator.trim() === "") {
    throw new BadUserInputError(
      "collaborator must be a non-empty username",
      "collaborator",
    );
  }
}

export type CollaboratorData = {
  id?: number;
  login?: string;
  fullName?: string;
  email?: string;
  active?: boolean;
  isAdmin?: boolean;
  created?: string;
  lastLogin?: string;
  permission?: "read" | "write" | "admin";
};

export type CollaboratorPermissionData = {
  permission?: string;
  roleName?: string;
  user?: {
    id?: number;
    login?: string;
    fullName?: string;
    email?: string;
    active?: boolean;
    isAdmin?: boolean;
    created?: string;
    lastLogin?: string;
  };
};

export interface ILedgerCollaboratorsWorkflow {
  addOrUpdateCollaborator(params: {
    identity: Identity;
    ledgerId: string;
    collaborator: string;
    permission?: "read" | "write" | "admin";
  }): Promise<{ success: boolean; message?: string }>;

  deleteCollaborator(params: {
    identity: Identity;
    ledgerId: string;
    collaborator: string;
  }): Promise<{ success: boolean; message?: string }>;

  listCollaborators(params: {
    identity: Identity;
    ledgerId: string;
    page?: number;
    limit?: number;
  }): Promise<CollaboratorData[]>;

  getCollaboratorPermission(params: {
    identity: Identity;
    ledgerId: string;
    collaborator: string;
  }): Promise<CollaboratorPermissionData>;

  leaveLedger(params: {
    identity: Identity;
    ledgerId: string;
  }): Promise<{ success: boolean; message?: string }>;
}

export class LedgerCollaboratorsWorkflow implements ILedgerCollaboratorsWorkflow {
  constructor(
    private readonly favaClientFactory: IFavaClientFactory,
    private readonly stripe: IStripeService,
    private readonly authorization: IAuthorizationService,
    private readonly models: Pick<IModels, "user">,
    private readonly db: DbExecutor,
  ) {}

  /**
   * The collaborator limit is the ledger owner's plan, whoever adds the
   * collaborator (PRFAQ005). A ledger owned by an organization with no
   * account behind it falls back to the acting user's plan.
   */
  private async ownerTier(ledgerOwner: string, actingUserId: string) {
    const owner = await this.models.user.getUserByUsername(
      this.db,
      ledgerOwner,
    );
    if (!owner) {
      moduleLogger.info("No account owns the ledger; using the actor's plan", {
        ledgerOwner,
      });
    }
    return getUserTier({
      stripe: this.stripe,
      userId: owner?.id ?? actingUserId,
    });
  }

  async addOrUpdateCollaborator(params: {
    identity: Identity;
    ledgerId: string;
    collaborator: string;
    permission?: "read" | "write" | "admin";
  }): Promise<{ success: boolean; message?: string }> {
    const { identity, ledgerId, collaborator, permission } = params;
    assertCollaboratorName(collaborator);
    await this.authorization.authorizeOrThrow({
      principal: identity,
      action: AUTHORIZATION_ACTIONS.LEDGER_COLLABORATORS_UPDATE,
      resource: ledgerResource(ledgerId),
    });
    const userId = identity.userId;
    const { ledgerOwner, ledgerName } = parseLedgerId(ledgerId);
    const [favaApiClient, ownerTier] = await Promise.all([
      this.favaClientFactory.getPublicApiClient(ledgerId, userId),
      this.ownerTier(ledgerOwner, userId),
    ]);
    const { maxCollaboratorsPerLedger: max } = getTierLimits(ownerTier);

    if (max !== -1) {
      // A list that cannot be read refuses the change rather than skipping
      // the limit.
      const existing = await readGiteaPages((query) =>
        unwrapFavaResponse(
          favaApiClient.collaborators.listLedgerCollaborators(
            ledgerOwner,
            ledgerName,
            query,
          ),
          "list collaborators",
        ),
      );
      // Gitea logins are case-insensitive.
      const is = (login: string | null | undefined, name: string) =>
        login?.toLowerCase() === name.toLowerCase();
      const isNew = !existing.some((c) => is(c.login, collaborator));
      const count = existing.filter((c) => !is(c.login, ledgerOwner)).length;

      // Changing an existing collaborator's permission never counts.
      if (isNew && count >= max) {
        throw new ResourceLimitReachedError(
          "Collaborator",
          max,
          count,
          `This ledger already has ${count} collaborators, the most its owner's ${TIER_DISPLAY_NAMES[ownerTier]} plan allows (${max}). The ledger owner can upgrade for more.`,
        );
      }
    }

    let response;
    try {
      response =
        await favaApiClient.collaborators.addOrUpdateLedgerCollaborator(
          ledgerOwner,
          ledgerName,
          collaborator,
          { permission: permission || null },
        );
    } catch (error) {
      throw translateUnknownUser(error, collaborator);
    }

    if (response.data?.success) {
      return {
        success: true,
        message: "Collaborator added/updated successfully",
      };
    }

    throw new InternalServerError("Failed to add/update collaborator");
  }

  async deleteCollaborator(params: {
    identity: Identity;
    ledgerId: string;
    collaborator: string;
  }): Promise<{ success: boolean; message?: string }> {
    const { identity, ledgerId, collaborator } = params;
    assertCollaboratorName(collaborator);
    await this.authorization.authorizeOrThrow({
      principal: identity,
      action: AUTHORIZATION_ACTIONS.LEDGER_COLLABORATORS_DELETE,
      resource: ledgerResource(ledgerId),
    });
    const userId = identity.userId;
    const favaApiClient = await this.favaClientFactory.getPublicApiClient(
      ledgerId,
      userId,
    );
    const { ledgerOwner, ledgerName } = parseLedgerId(ledgerId);

    let response;
    try {
      response = await favaApiClient.collaborators.deleteLedgerCollaborator(
        ledgerOwner,
        ledgerName,
        collaborator,
      );
    } catch (error) {
      throw translateUnknownUser(error, collaborator);
    }

    if (response.data?.success) {
      return { success: true, message: "Collaborator deleted successfully" };
    }

    throw new InternalServerError("Failed to delete collaborator");
  }

  async listCollaborators(params: {
    identity: Identity;
    ledgerId: string;
    page?: number;
    limit?: number;
  }): Promise<CollaboratorData[]> {
    const { identity, ledgerId, page = 1, limit = 10 } = params;
    await this.authorization.authorizeOrThrow({
      principal: identity,
      action: AUTHORIZATION_ACTIONS.LEDGER_COLLABORATORS_LIST,
      resource: ledgerResource(ledgerId),
    });
    const userId = identity.userId;
    const favaApiClient = await this.favaClientFactory.getPublicApiClient(
      ledgerId,
      userId,
    );
    const { ledgerOwner, ledgerName } = parseLedgerId(ledgerId);

    const response = await favaApiClient.collaborators.listLedgerCollaborators(
      ledgerOwner,
      ledgerName,
      { page, limit },
    );

    if (!response.data?.success || !response.data.data) {
      throw new InternalServerError("Failed to fetch collaborators");
    }

    const validPermissions = ["read", "write", "admin"] as const;

    const permissionResults = await Promise.allSettled(
      response.data.data.map(async (user: UserPublic) => {
        const permission =
          await favaApiClient.collaborators.getLedgerCollaboratorPermission(
            ledgerOwner,
            ledgerName,
            user.login ?? "",
          );
        return { user, permission };
      }),
    );

    return permissionResults
      .map((result) => {
        if (result.status === "rejected") {
          moduleLogger.error("Failed to fetch collaborator permission", {
            reason: result.reason,
          });
          return null;
        }

        const { user, permission } = result.value;
        const permissionValue = permission.data?.data?.permission;
        const validatedPermission =
          permissionValue &&
          validPermissions.includes(
            permissionValue as (typeof validPermissions)[number],
          )
            ? (permissionValue as "read" | "write" | "admin")
            : undefined;

        return {
          id: user.id ?? undefined,
          login: user.login ?? undefined,
          fullName: user.full_name ?? undefined,
          email: user.email ?? undefined,
          active: user.active ?? undefined,
          isAdmin: user.is_admin ?? undefined,
          created: user.created ?? undefined,
          lastLogin: user.last_login ?? undefined,
          permission: validatedPermission,
        };
      })
      .filter((c): c is NonNullable<typeof c> => c !== null);
  }

  async getCollaboratorPermission(params: {
    identity: Identity;
    ledgerId: string;
    collaborator: string;
  }): Promise<CollaboratorPermissionData> {
    const { identity, ledgerId, collaborator } = params;
    assertCollaboratorName(collaborator);
    await this.authorization.authorizeOrThrow({
      principal: identity,
      action: AUTHORIZATION_ACTIONS.LEDGER_COLLABORATORS_PERMISSION_READ,
      resource: ledgerResource(ledgerId),
    });
    const userId = identity.userId;
    const favaApiClient = await this.favaClientFactory.getPublicApiClient(
      ledgerId,
      userId,
    );
    const { ledgerOwner, ledgerName } = parseLedgerId(ledgerId);

    let response;
    try {
      response =
        await favaApiClient.collaborators.getLedgerCollaboratorPermission(
          ledgerOwner,
          ledgerName,
          collaborator,
        );
    } catch (error) {
      throw translateUnknownUser(error, collaborator);
    }

    if (!response.data?.success || !response.data.data) {
      throw new InternalServerError("Failed to fetch collaborator permission");
    }

    const data = response.data.data;
    return {
      permission: data.permission ?? undefined,
      roleName: data.role_name ?? undefined,
      user: data.user
        ? {
            id: data.user.id ?? undefined,
            login: data.user.login ?? undefined,
            fullName: data.user.full_name ?? undefined,
            email: data.user.email ?? undefined,
            active: data.user.active ?? undefined,
            isAdmin: data.user.is_admin ?? undefined,
            created: data.user.created ?? undefined,
            lastLogin: data.user.last_login ?? undefined,
          }
        : undefined,
    };
  }

  async leaveLedger(params: {
    identity: Identity;
    ledgerId: string;
  }): Promise<{ success: boolean; message?: string }> {
    const { identity, ledgerId } = params;
    await this.authorization.authorizeOrThrow({
      principal: identity,
      action: AUTHORIZATION_ACTIONS.LEDGER_COLLABORATORS_LEAVE,
      resource: ledgerResource(ledgerId),
    });
    const userId = identity.userId;
    const { favaUser } = await this.favaClientFactory.getApiContext(userId);
    const favaAdminApiClient = this.favaClientFactory.getAdminClient();
    const { ledgerOwner, ledgerName } = parseLedgerId(ledgerId);

    const response =
      await favaAdminApiClient.collaborators.deleteLedgerCollaborator(
        ledgerOwner,
        ledgerName,
        favaUser.username,
      );

    if (response.data?.success) {
      return {
        success: true,
        message: "Removed self from repository successfully",
      };
    }

    throw new InternalServerError("Failed to remove self from repository");
  }
}
