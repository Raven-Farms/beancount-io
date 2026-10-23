import * as SecureStore from "expo-secure-store";

const ACCOUNT_CHOICE_KEY = "oauth-account-choice-next";

/**
 * Remembers that the user signed out, until the next sign-in completes.
 * Sign-in reuses the system browser's session, which sign-out cannot end, so
 * the next Sign In approved the previous account with one tap and no
 * password (w21/153). While this is set, sign-in asks the server for an
 * explicit account choice instead.
 */
export async function markAccountChoiceNeeded(): Promise<void> {
  await SecureStore.setItemAsync(ACCOUNT_CHOICE_KEY, "1");
}

export async function isAccountChoiceNeeded(): Promise<boolean> {
  try {
    return (await SecureStore.getItemAsync(ACCOUNT_CHOICE_KEY)) === "1";
  } catch {
    return false;
  }
}

export async function clearAccountChoiceNeeded(): Promise<void> {
  await SecureStore.deleteItemAsync(ACCOUNT_CHOICE_KEY);
}
