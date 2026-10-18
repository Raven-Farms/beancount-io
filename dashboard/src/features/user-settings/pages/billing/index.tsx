import { Navigate } from "@tanstack/react-router";
import { PageSEO } from "@/common/components/seo/page-seo";
import { useTranslations } from "@/common/hooks/use-translations";
import { useReactNativeContext } from "@/common/providers/react-native-bridge-provider/react-native-bridge-context";
import { SubscriptionSection } from "../general/subscription-section";

/**
 * Settings → Billing: the plan summary, the yearly offer, every plan, and the
 * billing actions. The native app's web view never shows billing (it does not
 * prompt for purchases), so it lands on the general settings instead.
 */
export default function BillingSettingsPage() {
  const { t } = useTranslations();
  const { isReactNative } = useReactNativeContext();
  if (isReactNative) return <Navigate to="/settings/general" replace />;
  return (
    <>
      <PageSEO titleKey="userSettings.billing" noIndex />
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold">{t("userSettings.billing")}</h1>
        <SubscriptionSection />
      </div>
    </>
  );
}
