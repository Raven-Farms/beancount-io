import { type DbExecutor } from "@/drizzle/drizzle";

/**
 * Account-level control over what the OAuth provider has issued to a user.
 *
 * oidc-provider stores its grants, refresh tokens and sessions through the
 * adapter in `oauth-adapter-model`, one row at a time and keyed by its own ids.
 * This model works across all of them for one user, which the provider itself
 * never does.
 */
export interface IOauthGrantModel {
  /**
   * Delete every grant the user holds, every row issued under those grants
   * (refresh tokens, authorization codes, stored access tokens) and the user's
   * provider sessions, for every client. Already-issued JWT access tokens are
   * not stored and run out on their own (one hour); nothing can refresh them.
   */
  revokeAllForUser(db: DbExecutor, userId: string): Promise<void>;
}
