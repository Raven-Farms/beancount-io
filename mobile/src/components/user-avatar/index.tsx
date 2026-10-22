import { useEffect, useState } from "react";
import { Image, PixelRatio, StyleSheet, Text, View } from "react-native";
import { useTheme } from "@/common/theme";
import {
  avatarImageUri,
  imageIsMissing,
  userInitials,
} from "@/common/user-display";

type UserAvatarProps = {
  uri?: string | null;
  name: string;
  size: number;
  testID?: string;
  /**
   * Told whether there is no picture: none given, or the server answered that
   * it does not exist. A Gravatar URL is returned for everyone without an
   * upload, so only a 404 says there is no Gravatar (w21/289). A load that
   * failed for any other reason (offline, slow) shows the initials but is not
   * reported, so the caller does not tell someone with a Gravatar to add one
   * (w21/430).
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
  const [missingSource, setMissingSource] = useState<string>();
  const showImage = source !== undefined && source !== failedSource;
  // The failed load says nothing about why; ask the server.
  useEffect(() => {
    if (failedSource === undefined || failedSource === missingSource) return;
    let current = true;
    void imageIsMissing(failedSource).then((missing) => {
      if (current && missing) setMissingSource(failedSource);
    });
    return () => {
      current = false;
    };
  }, [failedSource, missingSource]);
  const noPicture = source === undefined || source === missingSource;
  useEffect(() => {
    onFallbackChange?.(noPicture);
  }, [noPicture, onFallbackChange]);
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
