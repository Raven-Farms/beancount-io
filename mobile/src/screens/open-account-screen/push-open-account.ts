// Relative, not `@/`, so the jest-lite runner can require this module — the
// same reason `push-account-picker.ts` avoids the alias.
import type { useRouter } from "expo-router";
import { AccountCreated } from "../../common/globalFnFactory";
import type { AccountRootPrefix } from "./account-name";

type OpenAccountRouter = Pick<ReturnType<typeof useRouter>, "push">;

interface PushOpenAccountOptions {
  /** Free-typed account name to seed the form with, verbatim. */
  prefill: string;
  /** Root to fall back to when `prefill` names no canonical root. */
  prefillRoot: AccountRootPrefix;
  /**
   * The dated entry's `YYYY-MM-DD` when reached from one, so the account opens
   * by then (w21/008). Open Account validates it and otherwise uses today.
   */
  openDate?: string;
  /** Receives the opened account. One-shot; consumed on the first success. */
  onCreated: (account: string) => void;
}

/**
 * Open the open-account screen prefilled and register who receives the new
 * account. Registration and push are one call for the same reason they are in
 * `pushAccountPicker`: registered-without-pushing (or vice versa) is
 * unrepresentable. The screen consumes the registration one-shot on success
 * (`runAccountCreatedCallback`) and discards it on unmount, so a cancelled
 * create cannot leak the callback into a later visit.
 */
export const pushOpenAccount = (
  router: OpenAccountRouter,
  { prefill, prefillRoot, openDate, onCreated }: PushOpenAccountOptions,
): void => {
  AccountCreated.setFn(onCreated);
  router.push({
    pathname: "/(app)/open-account",
    params: { prefill, prefillRoot, ...(openDate ? { openDate } : {}) },
  });
};
