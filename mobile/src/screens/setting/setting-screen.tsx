import { Stack } from "expo-router";
import { useTheme } from "@/common/theme";
import { About } from "./about";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTranslations } from "@/common/hooks/use-translations";

export function SettingScreen(): JSX.Element {
  const theme = useTheme().colorTheme;
  const { t } = useTranslations();

  // No ledger guard: nothing here reads a ledger, and Log out and Delete
  // account must stay reachable for a user with no usable ledger (w21/217).
  return (
    <>
      <Stack.Screen options={{ title: t("settings") }} />
      <SafeAreaView
        edges={["bottom"]}
        style={{
          backgroundColor: theme.white,
          flex: 1,
        }}
      >
        <About />
      </SafeAreaView>
    </>
  );
}
