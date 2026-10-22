import { Pressable, StyleSheet, Text, View } from "react-native";
import { useThemeStyle } from "@/common/hooks/use-theme-style";
import { useTranslations } from "@/common/hooks/use-translations";
import { fontSizes } from "@/common/theme";
import { ColorTheme } from "@/types/theme-props";

const getStyles = (theme: ColorTheme) =>
  StyleSheet.create({
    row: {
      alignItems: "center",
      paddingVertical: 20,
      gap: 8,
    },
    message: {
      fontSize: fontSizes.md,
      color: theme.black60,
    },
    retry: {
      fontSize: fontSizes.md,
      fontWeight: "600",
      color: theme.primary,
    },
  });

/**
 * The footer of a paged list whose next page failed to load: that it did, and
 * a way to ask again. Without it the list simply ended and read as the whole
 * history (w21/353).
 */
export function LoadMoreFailed({ onRetry }: { onRetry: () => void }) {
  const styles = useThemeStyle(getStyles);
  const { t } = useTranslations();
  return (
    <View style={styles.row} testID="load-more-failed">
      <Text style={styles.message}>{t("loadMoreFailed")}</Text>
      <Pressable
        onPress={onRetry}
        accessibilityRole="button"
        hitSlop={8}
        testID="load-more-retry"
      >
        <Text style={styles.retry}>{t("discoveryRetry")}</Text>
      </Pressable>
    </View>
  );
}
