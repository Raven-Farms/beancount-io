import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import { Stack, router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  LedgerOpeningState,
  LedgerTemplate,
  useCreateLedgerMutation,
  usePreviewLedgerSetupLazyQuery,
} from "@/generated-graphql/graphql";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Localization from "expo-localization";
import { SETUP_PRESETS, suggestCurrency } from "./setup-presets";
import { useThemeStyle } from "@/common/hooks/use-theme-style";
import { useTranslations } from "@/common/hooks/use-translations";
import {
  fontSizes,
  fontWeights,
  gutter,
  headerActionMaxFontSizeMultiplier,
  headerActionStyle,
  space,
  useTheme,
} from "@/common/theme";
import { useLedgerDirectory } from "@/common/ledger-directory/ledger-directory-provider";
import { ledgerVar } from "@/common/vars";
import { LEADING_TEXT_ALIGN, leadingInputTextAlign } from "@/common/rtl";
import type { ColorTheme } from "@/types/theme-props";
import {
  classifyCreateLedgerError,
  generateDefaultLedgerName,
  slugifyLedgerName,
  ledgerSlugPreview,
} from "./ledger-name";

type FormValues = {
  name: string;
  description: string;
  private: boolean;
  template: "STARTER" | "SAMPLE";
  currency: string;
  historyStart: string;
  openingAccount: string;
  openingAmount: string;
};

type StartKind = "starter" | "sample" | "preset";

const DRAFT_KEY = "create-ledger-draft";

interface CreateDraft {
  step: number;
  startKind: StartKind;
  presetId: string | null;
  requestId: string;
  values: FormValues;
}

function newRequestId(): string {
  return `req-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

const getStyles = (theme: ColorTheme) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: theme.white,
    },
    doneButton: headerActionStyle(theme),
    doneButtonDisabled: {
      color: theme.black60,
    },
    content: {
      paddingHorizontal: gutter,
      paddingTop: space.md,
      paddingBottom: space.xl,
      gap: space.md,
    },
    card: {
      borderWidth: StyleSheet.hairlineWidth,
      borderColor: theme.black20,
      borderRadius: 12,
      backgroundColor: theme.white,
      overflow: "hidden",
    },
    row: {
      minHeight: 58,
      paddingHorizontal: space.md,
      paddingVertical: space.sm,
      gap: space.xs,
    },
    rowDivider: {
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: theme.black20,
    },
    label: {
      color: theme.black80,
      fontSize: fontSizes.sm,
      fontWeight: fontWeights.medium,
      textAlign: LEADING_TEXT_ALIGN,
    },
    input: {
      color: theme.text01,
      fontSize: fontSizes.md,
      paddingVertical: space.xs,
      textAlign: leadingInputTextAlign(),
    },
    hint: {
      color: theme.black80,
      fontSize: fontSizes.sm,
      textAlign: LEADING_TEXT_ALIGN,
    },
    error: {
      color: theme.error,
      fontSize: fontSizes.sm,
      textAlign: LEADING_TEXT_ALIGN,
      paddingHorizontal: space.md,
      paddingBottom: space.sm,
    },
    switchRow: {
      minHeight: 58,
      paddingHorizontal: space.md,
      paddingVertical: space.sm,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      gap: space.md,
    },
    templateRow: {
      minHeight: 72,
      paddingHorizontal: space.md,
      paddingVertical: space.sm,
      gap: space.xs,
    },
    templateSelected: {
      backgroundColor: theme.black10,
    },
    templateTitle: {
      color: theme.text01,
      fontSize: fontSizes.md,
      fontWeight: fontWeights.medium,
      textAlign: LEADING_TEXT_ALIGN,
    },
    formError: {
      color: theme.error,
      fontSize: fontSizes.md,
      textAlign: LEADING_TEXT_ALIGN,
      paddingHorizontal: gutter,
    },
  });

export function CreateLedgerScreen(): JSX.Element {
  const { t } = useTranslations();
  const theme = useTheme().colorTheme;
  const styles = useThemeStyle(getStyles);
  const { ledgers, loading: directoryLoading, refresh } = useLedgerDirectory();
  const [createLedger, { loading }] = useCreateLedgerMutation();
  const [
    runPreview,
    { data: previewData, loading: previewLoading, error: previewError },
  ] = usePreviewLedgerSetupLazyQuery();
  const [step, setStep] = useState(0);
  const [startKind, setStartKind] = useState<StartKind>("starter");
  const [presetId, setPresetId] = useState<string | null>(SETUP_PRESETS[0].id);
  const requestIdRef = useRef<string>(newRequestId());

  const schema = useMemo(
    () =>
      z.object({
        name: z
          .string()
          .min(1, t("createLedgerNameRequired"))
          .max(100, t("createLedgerNameMaxLength"))
          .refine((val) => slugifyLedgerName(val).length > 0, {
            message: t("createLedgerNameInvalid"),
          }),
        description: z.string(),
        private: z.boolean(),
        template: z.enum(["STARTER", "SAMPLE"]),
        currency: z.string(),
        historyStart: z.string(),
        openingAccount: z.string(),
        openingAmount: z
          .string()
          .refine((val) => !val || /^-?\d+(\.\d+)?$/.test(val), {
            message: t("createLedgerAmountInvalid"),
          }),
      }),
    [t],
  );

  const existingNames = useMemo(
    () => ledgers.map((ledger) => ledger.name),
    [ledgers],
  );

  const {
    control,
    handleSubmit,
    getValues,
    reset,
    setValue,
    setError,
    trigger,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      description: "",
      private: true,
      template: "STARTER",
      currency: suggestCurrency(Localization.getLocales()[0]?.regionCode),
      historyStart: new Date().toISOString().slice(0, 10),
      openingAccount: "",
      openingAmount: "",
    },
  });

  // Restore a draft left by leaving this screen (ADR021: resume, never
  // duplicate). The requestId is restored with it, so a retried submission
  // after an OTP round-trip returns the original ledger.
  const restoredRef = useRef(false);
  useEffect(() => {
    if (restoredRef.current) return;
    restoredRef.current = true;
    void AsyncStorage.getItem(DRAFT_KEY).then((raw) => {
      if (!raw) return;
      try {
        const draft = JSON.parse(raw) as CreateDraft;
        setStep(draft.step);
        setStartKind(draft.startKind);
        setPresetId(draft.presetId);
        requestIdRef.current = draft.requestId;
        reset(draft.values);
      } catch {
        // A corrupt draft is ignored; the flow starts fresh.
      }
    });
  }, [reset]);

  const watched = watch();
  useEffect(() => {
    const draft: CreateDraft = {
      step,
      startKind,
      presetId,
      requestId: requestIdRef.current,
      values: watched,
    };
    void AsyncStorage.setItem(DRAFT_KEY, JSON.stringify(draft)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, startKind, presetId, JSON.stringify(watched)]);

  useEffect(() => {
    if (watch("name")) return;
    if (directoryLoading) return;
    setValue("name", generateDefaultLedgerName(existingNames));
    // Only seed once list data arrives and name is still empty.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [directoryLoading, existingNames.join("|")]);

  const preset = SETUP_PRESETS.find((entry) => entry.id === presetId);
  const moneyAccounts =
    preset?.accounts.filter((account) => account.money) ?? [];

  const buildSetup = (values: FormValues) => {
    if (!preset) return undefined;
    const amount = values.openingAmount.trim();
    return {
      preset: preset.id,
      title: values.name,
      operatingCurrency: (values.currency || "USD").toUpperCase(),
      historyStart: values.historyStart || undefined,
      accounts:
        amount && values.openingAccount
          ? [
              {
                name: values.openingAccount,
                openingState: LedgerOpeningState.Known,
                amount,
              },
            ]
          : undefined,
    };
  };

  useEffect(() => {
    if (step === 2 && startKind === "preset") {
      const setup = buildSetup(getValues());
      if (setup) void runPreview({ variables: { setup } });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, startKind]);

  const nameValue = watch("name");
  const slugPreview = ledgerSlugPreview(nameValue ?? "");
  const busy = loading || isSubmitting;

  const onSubmit = handleSubmit(async (values) => {
    const name = slugifyLedgerName(values.name);
    try {
      const result = await createLedger({
        variables: {
          name,
          private: values.private,
          description: values.description.trim() || undefined,
          ...(startKind === "sample"
            ? { template: LedgerTemplate.Sample }
            : {}),
          ...(startKind === "preset" ? { setup: buildSetup(values) } : {}),
          requestId: requestIdRef.current,
        },
      });
      void AsyncStorage.removeItem(DRAFT_KEY).catch(() => {});
      const id = result.data?.createLedger?.id;
      if (!id) {
        setError("root", { message: t("createLedgerGenericError") });
        return;
      }
      // The creation already succeeded. A failed list refresh must not invite
      // another submission; the directory retains the confirmed new ledger.
      await refresh(result.data!.createLedger).catch(() => {});
      ledgerVar(id);
      router.replace("/(app)/(tabs)");
    } catch (error) {
      const kind = classifyCreateLedgerError(error);
      if (kind === "conflict") {
        setError("name", { message: t("createLedgerNameConflict") });
        return;
      }
      if (kind === "tier") {
        setError("root", { message: t("createLedgerTierLimit") });
        return;
      }
      setError("root", { message: t("createLedgerGenericError") });
    }
  });

  return (
    <SafeAreaView style={styles.container} edges={["bottom"]}>
      <Stack.Screen
        options={{
          title: t("createLedgerTitle"),
          headerRight: () => (
            <Pressable
              onPress={() => {
                if (step < 2) {
                  void (async () => {
                    if (step === 1 && !(await trigger("name"))) return;
                    setStep((current) => Math.min(current + 1, 2));
                  })();
                } else {
                  void onSubmit();
                }
              }}
              disabled={busy}
              accessibilityRole="button"
              accessibilityLabel={
                step < 2 ? t("createLedgerNext") : t("createLedgerSubmit")
              }
              hitSlop={8}
            >
              {busy ? (
                <ActivityIndicator color={theme.primary} />
              ) : (
                <Text
                  style={[
                    styles.doneButton,
                    busy ? styles.doneButtonDisabled : null,
                  ]}
                  maxFontSizeMultiplier={headerActionMaxFontSizeMultiplier}
                >
                  {step < 2 ? t("createLedgerNext") : t("createLedgerSubmit")}
                </Text>
              )}
            </Pressable>
          ),
        }}
      />
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        automaticallyAdjustKeyboardInsets={Platform.OS === "ios"}
      >
        <Text style={styles.hint} testID="create-ledger-step">
          {t("createLedgerStep", { step: step + 1, total: 3 })}
        </Text>
        {step === 0 ? (
          <>
            <Text style={styles.label}>{t("createLedgerTemplate")}</Text>
            <View style={styles.card}>
              {(
                [
                  [
                    "starter",
                    "createLedgerTemplateStarter",
                    "createLedgerTemplateStarterHint",
                  ],
                  [
                    "sample",
                    "createLedgerTemplateSample",
                    "createLedgerTemplateSampleHint",
                  ],
                  [
                    "preset",
                    "createLedgerStartPreset",
                    "createLedgerReviewDescription",
                  ],
                ] as const
              ).map(([kind, titleKey, hintKey]) => (
                <Pressable
                  key={kind}
                  onPress={() => setStartKind(kind)}
                  style={[
                    styles.templateRow,
                    startKind === kind ? styles.templateSelected : null,
                  ]}
                  accessibilityRole="button"
                  accessibilityState={{ selected: startKind === kind }}
                  accessibilityLabel={t(titleKey)}
                >
                  <Text style={styles.templateTitle}>{t(titleKey)}</Text>
                  <Text style={styles.hint}>{t(hintKey)}</Text>
                </Pressable>
              ))}
            </View>
            {startKind === "preset" ? (
              <View style={styles.card} testID="setup-preset-list">
                {SETUP_PRESETS.map((entry) => (
                  <Pressable
                    key={entry.id}
                    onPress={() => setPresetId(entry.id)}
                    style={[
                      styles.templateRow,
                      presetId === entry.id ? styles.templateSelected : null,
                    ]}
                    accessibilityRole="button"
                    accessibilityState={{ selected: presetId === entry.id }}
                    accessibilityLabel={t(entry.titleKey)}
                  >
                    <Text style={styles.templateTitle}>
                      {t(entry.titleKey)}
                    </Text>
                    <Text style={styles.hint}>{t(entry.outcomeKey)}</Text>
                  </Pressable>
                ))}
              </View>
            ) : null}
          </>
        ) : null}
        {step === 1 ? (
          <View style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.label}>{t("createLedgerName")}</Text>
              <Controller
                control={control}
                name="name"
                render={({ field: { onChange, onBlur, value } }) => (
                  <TextInput
                    value={value}
                    onChangeText={onChange}
                    onBlur={onBlur}
                    autoCapitalize="none"
                    autoCorrect={false}
                    placeholder={t("createLedgerNamePlaceholder")}
                    placeholderTextColor={theme.black40}
                    style={styles.input}
                    accessibilityLabel={t("createLedgerName")}
                  />
                )}
              />
              {slugPreview ? (
                <Text style={styles.hint}>
                  {t("createLedgerSlugPreview", { slug: slugPreview })}
                </Text>
              ) : null}
            </View>
            {errors.name?.message ? (
              <Text style={styles.error}>{errors.name.message}</Text>
            ) : null}

            <View style={[styles.row, styles.rowDivider]}>
              <Text style={styles.label}>{t("createLedgerDescription")}</Text>
              <Controller
                control={control}
                name="description"
                render={({ field: { onChange, onBlur, value } }) => (
                  <TextInput
                    value={value}
                    onChangeText={onChange}
                    onBlur={onBlur}
                    placeholder={t("createLedgerDescriptionPlaceholder")}
                    placeholderTextColor={theme.black40}
                    style={styles.input}
                    accessibilityLabel={t("createLedgerDescription")}
                  />
                )}
              />
            </View>

            <View style={[styles.switchRow, styles.rowDivider]}>
              <Text style={styles.label}>{t("createLedgerPrivate")}</Text>
              <Controller
                control={control}
                name="private"
                render={({ field: { onChange, value } }) => (
                  <Switch
                    value={value}
                    onValueChange={onChange}
                    trackColor={{ false: theme.black20, true: theme.primary }}
                    accessibilityLabel={t("createLedgerPrivate")}
                  />
                )}
              />
            </View>
          </View>
        ) : null}
        {step === 1 && startKind === "preset" ? (
          <View style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.label}>{t("createLedgerCurrency")}</Text>
              <Controller
                control={control}
                name="currency"
                render={({ field: { onChange, onBlur, value } }) => (
                  <TextInput
                    value={value}
                    onChangeText={(text) => onChange(text.toUpperCase())}
                    onBlur={onBlur}
                    autoCapitalize="characters"
                    autoCorrect={false}
                    maxLength={3}
                    style={styles.input}
                    accessibilityLabel={t("createLedgerCurrency")}
                  />
                )}
              />
            </View>
            <View style={[styles.row, styles.rowDivider]}>
              <Text style={styles.label}>{t("createLedgerHistoryStart")}</Text>
              <Controller
                control={control}
                name="historyStart"
                render={({ field: { onChange, onBlur, value } }) => (
                  <TextInput
                    value={value}
                    onChangeText={onChange}
                    onBlur={onBlur}
                    autoCapitalize="none"
                    autoCorrect={false}
                    placeholder="YYYY-MM-DD"
                    placeholderTextColor={theme.black40}
                    style={styles.input}
                    accessibilityLabel={t("createLedgerHistoryStart")}
                  />
                )}
              />
            </View>
            {moneyAccounts.length > 0 ? (
              <>
                <Text style={styles.label}>
                  {t("createLedgerOpeningAccount")}
                </Text>
                <Text style={styles.hint}>{t("createLedgerOpeningNone")}</Text>
                {moneyAccounts.map((account) => (
                  <Pressable
                    key={account.name}
                    onPress={() =>
                      setValue(
                        "openingAccount",
                        watch("openingAccount") === account.name
                          ? ""
                          : account.name,
                      )
                    }
                    style={[
                      styles.templateRow,
                      watch("openingAccount") === account.name
                        ? styles.templateSelected
                        : null,
                    ]}
                    accessibilityRole="button"
                    accessibilityState={{
                      selected: watch("openingAccount") === account.name,
                    }}
                    accessibilityLabel={account.name}
                  >
                    <Text style={styles.templateTitle}>{account.name}</Text>
                  </Pressable>
                ))}
                <View style={[styles.row, styles.rowDivider]}>
                  <Text style={styles.label}>
                    {t("createLedgerOpeningAmount")}
                  </Text>
                  <Controller
                    control={control}
                    name="openingAmount"
                    render={({ field: { onChange, onBlur, value } }) => (
                      <TextInput
                        value={value}
                        onChangeText={onChange}
                        onBlur={onBlur}
                        keyboardType="decimal-pad"
                        placeholder="0"
                        placeholderTextColor={theme.black40}
                        style={styles.input}
                        accessibilityLabel={t("createLedgerOpeningAmount")}
                      />
                    )}
                  />
                  {errors.openingAmount?.message ? (
                    <Text style={styles.error}>
                      {errors.openingAmount.message}
                    </Text>
                  ) : null}
                </View>
              </>
            ) : null}
          </View>
        ) : null}
        {step === 2 ? (
          <View style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.templateTitle}>
                {t("createLedgerReview")}
              </Text>
              <Text style={styles.hint}>
                {t("createLedgerReviewDescription")}
              </Text>
              <Text style={styles.hint}>{slugPreview || nameValue}</Text>
              {startKind === "preset" ? (
                previewLoading ? (
                  <ActivityIndicator color={theme.primary} />
                ) : previewError ? (
                  <Text style={styles.error}>{previewError.message}</Text>
                ) : previewData?.previewLedgerSetup ? (
                  <>
                    <Text style={styles.label}>
                      {t("createLedgerAccounts")}
                    </Text>
                    {previewData.previewLedgerSetup.accounts.map((account) => (
                      <Text key={account} style={styles.hint}>
                        {account}
                      </Text>
                    ))}
                  </>
                ) : null
              ) : null}
            </View>
          </View>
        ) : null}
        {step > 0 ? (
          <Pressable
            onPress={() => setStep((current) => Math.max(current - 1, 0))}
            accessibilityRole="button"
            accessibilityLabel={t("createLedgerBack")}
          >
            <Text style={styles.templateTitle}>{t("createLedgerBack")}</Text>
          </Pressable>
        ) : null}

        {errors.root?.message ? (
          <Text style={styles.formError}>{errors.root.message}</Text>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}
