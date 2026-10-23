/** The storage the marker lives in: the app's sandbox, which uninstall erases. */
export interface SandboxStorage {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  getAllKeys(): Promise<readonly string[]>;
}

const INSTALL_MARKER_KEY = "install-marker";

/**
 * Whether this launch is the first since the app was installed. iOS erases
 * the sandbox on uninstall but keeps Keychain items, so a reinstall restored
 * the previous account's session for up to a year (w21/154).
 *
 * A missing marker alone is not a fresh install: every install from before
 * the marker existed lacks it too, and signing all of them out on upgrade
 * would be its own bug. Only a sandbox with nothing in it at all is new.
 * Import-free so the unit runner can load it.
 */
export async function claimInstallMarker(
  storage: SandboxStorage,
): Promise<"fresh-install" | "known"> {
  if ((await storage.getItem(INSTALL_MARKER_KEY)) !== null) return "known";
  const keys = await storage.getAllKeys();
  await storage.setItem(INSTALL_MARKER_KEY, "1");
  return keys.length === 0 ? "fresh-install" : "known";
}
