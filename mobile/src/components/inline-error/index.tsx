import { useEffect } from "react";
import {
  AccessibilityInfo,
  Platform,
  Text,
  type TextStyle,
} from "react-native";
import type { StyleProp } from "react-native";

/**
 * An error shown under a field or a form. Android reads a live region when its
 * text changes; iOS has no such prop, so VoiceOver stayed silent when a save
 * was refused or an amount was unreadable (w21/354). The message is announced
 * there each time it changes.
 */
export function InlineError({
  message,
  style,
  testID,
}: {
  message: string;
  style?: StyleProp<TextStyle>;
  testID?: string;
}) {
  useEffect(() => {
    if (Platform.OS === "ios")
      AccessibilityInfo.announceForAccessibility(message);
  }, [message]);
  return (
    <Text
      style={style}
      accessibilityRole="alert"
      accessibilityLiveRegion="polite"
      testID={testID}
    >
      {message}
    </Text>
  );
}
