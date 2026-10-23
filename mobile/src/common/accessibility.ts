import { Platform } from "react-native";

type Translate = (key: string) => string;

/**
 * Props for a row that expands and collapses. iOS speaks "expanded" for the
 * state but never "collapsed", so a closed row sounded like a plain button;
 * the hint says what a double tap does in either state (w21/356).
 */
export function disclosureAccessibility(expanded: boolean, t: Translate) {
  return {
    accessibilityState: { expanded },
    accessibilityHint: t(expanded ? "a11yTapToCollapse" : "a11yTapToExpand"),
  } as const;
}

/**
 * The role for a tab button. Fabric maps only `tabbar` to an iOS trait, so a
 * `tab` there carries none and an unselected tab did not sound tappable; a
 * `button` plus the selected state reads right on iOS, and Android keeps the
 * tab role (w21/356).
 */
export const tabRole = Platform.OS === "ios" ? "button" : "tab";
