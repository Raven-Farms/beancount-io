import { Slot } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { Providers } from "@/common/providers/providers";
import { AppLinkHandler } from "@/common/app-links/app-link-handler";

export default function RootLayout() {
  return (
    <Providers>
      {/* The base status bar. Scan Receipt mounts a light one over the camera;
          without this one, leaving it popped back to a built-in default that
          Android reads as light icons on the light theme (w21/403). `auto`
          follows the app's theme, which sets the native color scheme. */}
      <StatusBar style="auto" />
      <AppLinkHandler />
      <Slot />
    </Providers>
  );
}
