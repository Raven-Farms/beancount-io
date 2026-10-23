import { and, eq, inArray, or, sql } from "drizzle-orm";
import { type DbExecutor } from "@/drizzle/drizzle";
import { oauthAdapterStorage } from "../oauth-adapter-model/schema";
import type { IOauthGrantModel } from "./types";

/**
 * The user an adapter row belongs to. oidc-provider's `accountId` is the bare
 * user id for identity and account-wide grants and `userId:ledgerId` for a
 * grant pinned to one ledger (oidc-route.ts), so compare its first segment.
 */
const rowUserId = sql`split_part(${oauthAdapterStorage.payload}->>'accountId', ':', 1)`;

export class OauthGrantPostgresModel implements IOauthGrantModel {
  public async revokeAllForUser(db: DbExecutor, userId: string): Promise<void> {
    const ownedByUser = sql`${rowUserId} = ${userId}`;
    const grants = db
      .select({ id: oauthAdapterStorage.id })
      .from(oauthAdapterStorage)
      .where(and(eq(oauthAdapterStorage.model, "Grant"), ownedByUser));

    // Rows carrying the account (Grant, Session, RefreshToken, AuthorizationCode,
    // …) and rows that only carry a grant id. Clients and registration tokens
    // carry neither, so they stay.
    await db
      .delete(oauthAdapterStorage)
      .where(or(ownedByUser, inArray(oauthAdapterStorage.grantId, grants)));
  }
}
