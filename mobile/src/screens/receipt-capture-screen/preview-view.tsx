import { useEffect } from "react";
import {
  AccessibilityInfo,
  ActivityIndicator,
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { fontSizes, fontWeights } from "@/common/theme";
import { useTranslations } from "@/common/hooks/use-translations";
import { CHROME } from "./chrome";
import { RevealView, type ReceiptReveal } from "./reveal-view";
import type { CapturedShot } from "./camera-view";

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CHROME.background },
  image: { flex: 1 },
  actions: {
    position: "absolute",
    left: 20,
    right: 20,
    flexDirection: "row",
    justifyContent: "space-between",
  },
  pill: {
    paddingHorizontal: 32,
    paddingVertical: 15,
    borderRadius: 28,
    backgroundColor: CHROME.pillFill,
    minWidth: 132,
    alignItems: "center",
  },
  pillPressed: { backgroundColor: CHROME.pillFillPressed },
  pillText: {
    color: CHROME.pillText,
    fontSize: fontSizes.lg,
    fontWeight: fontWeights.medium,
  },
  // Full-screen blocking overlay over the still, not a content area waiting on a
  // query — a spinner is right here, a LoadingTile skeleton would not be.
  scrim: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: CHROME.scrim,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 32,
    gap: 18,
  },
  scrimText: {
    color: CHROME.icon,
    fontSize: fontSizes.lg,
    fontWeight: fontWeights.medium,
    textAlign: "center",
  },
  errorText: {
    color: CHROME.icon,
    fontSize: fontSizes.md,
    textAlign: "center",
    lineHeight: 22,
  },
  errorActions: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: 12,
    marginTop: 6,
  },
});

export const PreviewView = ({
  shot,
  status,
  errorMessage,
  reveal,
  onRetake,
  onUpload,
  onRetry,
  onCancel,
  onCancelBusy,
  uploadPercent,
}: {
  shot: CapturedShot;
  status: "preview" | "uploading" | "parsing" | "revealed" | "error";
  errorMessage?: string;
  /** What the parse extracted; required by the `revealed` status. */
  reveal?: ReceiptReveal;
  onRetake: () => void;
  onUpload: () => void;
  /** Run the upload again with the same photo; omitted when retrying is futile. */
  onRetry?: () => void;
  onCancel: () => void;
  /** Abandon the upload or parse in flight and return to the preview. */
  onCancelBusy: () => void;
  /** Whole-percent upload progress, `null` while unknown. */
  uploadPercent?: number | null;
}) => {
  const insets = useSafeAreaInsets();
  const { t } = useTranslations();

  const busyLabel =
    status === "uploading"
      ? uploadPercent == null
        ? t("receiptUploading")
        : t("receiptUploadingProgress", { percent: uploadPercent })
      : status === "parsing"
        ? t("receiptParsing")
        : null;

  // The focused button disappears when Upload is tapped, so each state that
  // replaces the controls is said aloud: uploading, parsing, the error and what
  // was read (w21/284). The percent is left out so a progress tick does not
  // repeat it.
  const announcement =
    status === "uploading"
      ? t("receiptUploading")
      : status === "parsing"
        ? t("receiptParsing")
        : status === "error"
          ? (errorMessage ?? null)
          : status === "revealed" && reveal
            ? t("receiptRevealSpoken", {
                summary: [reveal.payee, reveal.amount, reveal.date]
                  .filter(Boolean)
                  .join(", "),
              })
            : null;
  useEffect(() => {
    if (announcement) AccessibilityInfo.announceForAccessibility(announcement);
  }, [announcement]);

  return (
    <View style={styles.container}>
      <Image
        source={{ uri: shot.uri }}
        style={styles.image}
        resizeMode="contain"
      />

      {status === "preview" ? (
        <View style={[styles.actions, { bottom: insets.bottom + 28 }]}>
          <Pressable
            testID="receipt-retake"
            accessibilityRole="button"
            style={({ pressed }) => [
              styles.pill,
              pressed && styles.pillPressed,
            ]}
            onPress={onRetake}
          >
            <Text style={styles.pillText}>{t("receiptRetake")}</Text>
          </Pressable>
          <Pressable
            testID="receipt-upload"
            accessibilityRole="button"
            style={({ pressed }) => [
              styles.pill,
              pressed && styles.pillPressed,
            ]}
            onPress={onUpload}
          >
            <Text style={styles.pillText}>{t("receiptUpload")}</Text>
          </Pressable>
        </View>
      ) : null}

      {busyLabel ? (
        <View style={styles.scrim}>
          <ActivityIndicator size="large" color={CHROME.icon} />
          <Text style={styles.scrimText}>{busyLabel}</Text>
          <Pressable
            testID="receipt-busy-cancel"
            accessibilityRole="button"
            style={({ pressed }) => [
              styles.pill,
              pressed && styles.pillPressed,
            ]}
            onPress={onCancelBusy}
          >
            <Text style={styles.pillText}>{t("receiptCancel")}</Text>
          </Pressable>
        </View>
      ) : null}

      {status === "revealed" && reveal ? <RevealView {...reveal} /> : null}

      {status === "error" ? (
        <View style={styles.scrim}>
          <Text style={styles.errorText} accessibilityRole="alert">
            {errorMessage}
          </Text>
          <View style={styles.errorActions}>
            <Pressable
              testID="receipt-error-cancel"
              accessibilityRole="button"
              style={({ pressed }) => [
                styles.pill,
                pressed && styles.pillPressed,
              ]}
              onPress={onCancel}
            >
              <Text style={styles.pillText}>{t("receiptCancel")}</Text>
            </Pressable>
            {onRetry ? (
              <Pressable
                testID="receipt-error-retry"
                accessibilityRole="button"
                style={({ pressed }) => [
                  styles.pill,
                  pressed && styles.pillPressed,
                ]}
                onPress={onRetry}
              >
                <Text style={styles.pillText}>{t("receiptTryAgain")}</Text>
              </Pressable>
            ) : null}
            <Pressable
              testID="receipt-error-retake"
              accessibilityRole="button"
              style={({ pressed }) => [
                styles.pill,
                pressed && styles.pillPressed,
              ]}
              onPress={onRetake}
            >
              <Text style={styles.pillText}>{t("receiptRetake")}</Text>
            </Pressable>
          </View>
        </View>
      ) : null}
    </View>
  );
};
