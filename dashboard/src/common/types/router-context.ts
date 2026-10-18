import type { Localization } from "@/i18n/init";
import type { getClient } from "@/common/apollo/client";
import type { AuthStatus, UserProfile } from "@/common/server-fn/user";

export type RouterContext = {
  localization: Localization;
  client: ReturnType<typeof getClient>;
  userProfile?: UserProfile | null;
  /** Set by the root beforeLoad; "unavailable" means the probe failed, not signed out. */
  authStatus?: AuthStatus;
  authErrorKey?: string | undefined;
};
