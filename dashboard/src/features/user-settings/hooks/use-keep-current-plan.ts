import { toast } from "sonner";
import { useTranslations } from "@/common/hooks/use-translations";
import { useErrorMessage } from "@/common/lib/errors/error-message";
import { stripePlanConfig } from "../pages/general/stripe-config";
import { useCancelScheduledPlanChange } from "./use-plan-change";

/** Undo a scheduled plan change from the Scheduled panel. */
export const useKeepCurrentPlan = () => {
  const { t } = useTranslations();
  const formatError = useErrorMessage();
  const [cancelScheduled, { loading }] = useCancelScheduledPlanChange();

  /** Returns whether the scheduled change was undone. */
  const keepCurrent = async (): Promise<boolean> => {
    try {
      const response = await cancelScheduled({
        variables: { clientId: stripePlanConfig.clientId },
      });
      const result = response.data?.cancelScheduledPlanChange;
      if (result?.success) {
        toast.success(t("userSettings.scheduledKept"));
        return true;
      }
      toast.error(result?.message || t("userSettings.scheduledKeepFailed"));
      return false;
    } catch (error) {
      toast.error(formatError(error));
      return false;
    }
  };

  return { keepCurrent, loading };
};
