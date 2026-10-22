import { useEffect } from "react";
import { Alert } from "react-native";
import { useNavigation } from "expo-router";
import { usePreventRemove } from "expo-router/react-navigation";
import { useTranslations } from "@/common/hooks/use-translations";
import { registerUnsavedEditsGuard } from "@/common/unsaved-edits-guard";

/**
 * Ask before a screen with unsaved changes is left: Cancel stays with the
 * edits, Discard leaves. Built on `usePreventRemove`, which also blocks iOS's
 * native swipe-back. A plain `beforeRemove` listener does not, so a swipe
 * slid the screen away first and the alert then landed over the screen
 * behind, with Cancel leaving the stack broken (w21/150).
 *
 * `leavingSaved` is set by a screen that navigates away itself after a
 * successful save; that is not a discard.
 *
 * A dirty screen also registers with the unsaved-edits guard, so an app link to
 * another ledger asks before it switches `ledgerVar` under the draft: without
 * that, Cancel on the later "Discard?" left the draft bound to the other
 * ledger, and Done wrote it there (w21/580).
 */
export function useUnsavedChangesGuard(
  hasUnsavedChanges: boolean,
  leavingSaved?: { readonly current: boolean },
): void {
  const navigation = useNavigation();
  const { t } = useTranslations();
  useEffect(() => {
    if (!hasUnsavedChanges) return undefined;
    return registerUnsavedEditsGuard(
      () =>
        new Promise<boolean>((resolve) => {
          if (leavingSaved?.current) {
            resolve(true);
            return;
          }
          Alert.alert(
            t("ledgerEditorUnsavedTitle"),
            t("ledgerEditorUnsavedMessage"),
            [
              {
                text: t("cancel"),
                style: "cancel",
                onPress: () => resolve(false),
              },
              {
                text: t("ledgerEditorDiscardChanges"),
                style: "destructive",
                onPress: () => resolve(true),
              },
            ],
            { cancelable: true, onDismiss: () => resolve(false) },
          );
        }),
    );
  }, [hasUnsavedChanges, leavingSaved, t]);

  usePreventRemove(hasUnsavedChanges, ({ data }) => {
    if (leavingSaved?.current) {
      navigation.dispatch(data.action);
      return;
    }
    Alert.alert(
      t("ledgerEditorUnsavedTitle"),
      t("ledgerEditorUnsavedMessage"),
      [
        { text: t("cancel"), style: "cancel" },
        {
          text: t("ledgerEditorDiscardChanges"),
          style: "destructive",
          onPress: () => navigation.dispatch(data.action),
        },
      ],
    );
  });
}
