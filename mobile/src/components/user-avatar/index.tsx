import { useEffect, useState } from "react";
import { Image, PixelRatio, StyleSheet, Text, View } from "react-native";
import { useTheme } from "@/common/theme";
import { avatarImageUri, userInitials } from "@/common/user-display";

type UserAvatarProps = {
  uri?: string | null;
  name: string;
  size: number;
  testID?: string;
  /**
   * Told whether the picture is not what shows: no picture, or one that failed
   * to load. A Gravatar URL is returned for everyone without an upload, so
   * only a failed load says there is no Gravatar (w21/289).
   */
  onFallbackChange?: (fallback: boolean) => void;
};

/** A round account picture that falls back to the person's initials when
 * there is no picture or it fails to load. Decorative: the surrounding row
 * carries the name for screen readers. */
export function UserAvatar({
  uri,
  name,
  size,
  testID,
  onFallbackChange,
}: UserAvatarProps): JSX.Element {
  const theme = useTheme().colorTheme;
  const source = avatarImageUri(
    uri,
    PixelRatio.getPixelSizeForLayoutSize(size),
  );
  const [failedSource, setFailedSource] = useState<string>();
  const showImage = source !== undefined && source !== failedSource;
  useEffect(() => {
    onFallbackChange?.(!showImage);
  }, [showImage, onFallbackChange]);
  const circle = {
    width: size,
    height: size,
    borderRadius: size / 2,
  };

  return (
    <View
      testID={testID}
      accessible={false}
      importantForAccessibility="no-hide-descendants"
      style={[styles.base, circle, { backgroundColor: theme.controlSelected }]}
    >
      {showImage ? (
        <Image
          source={{ uri: source }}
          style={circle}
          onError={() => setFailedSource(source)}
        />
      ) : (
        <Text
          style={[
            styles.initials,
            { color: theme.primary, fontSize: Math.round(size * 0.4) },
          ]}
          allowFontScaling={false}
        >
          {userInitials(name)}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  initials: { fontWeight: "600" },
});
