import { Alert } from "react-native";
import { useNavigation } from "expo-router";
import { usePreventRemove } from "expo-router/react-navigation";
import { useTranslations } from "@/common/hooks/use-translations";

/**
 * Ask before a screen with unsaved changes is left: Cancel stays with the
 * edits, Discard leaves. Built on `usePreventRemove`, which also blocks iOS's
 * native swipe-back. A plain `beforeRemove` listener does not, so a swipe
 * slid the screen away first and the alert then landed over the screen
 * behind, with Cancel leaving the stack broken (w21/150).
 *
 * `leavingSaved` is set by a screen that navigates away itself after a
 * successful save; that is not a discard.
 */
export function useUnsavedChangesGuard(
  hasUnsavedChanges: boolean,
  leavingSaved?: { readonly current: boolean },
): void {
  const navigation = useNavigation();
  const { t } = useTranslations();
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
