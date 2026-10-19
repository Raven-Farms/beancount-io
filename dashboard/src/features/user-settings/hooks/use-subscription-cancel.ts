import { useState } from "react";
import { useMutation } from "@apollo/client/react";
import {
  type CancellationReason,
  CancelSubscriptionDocument,
  type CancelSubscriptionMutation,
  type CancelSubscriptionMutationVariables,
  GetSubscriptionStatusDocument,
} from "@/graphql/definitions";
import { toast } from "sonner";
import { useTranslations } from "@/common/hooks/use-translations";
import { useErrorMessage } from "@/common/lib/errors/error-message";

/** The subscription the cancel sheet is about: its id and when it ends. */
export interface CancelTarget {
  id: string;
  clientId: string;
  /** ISO period end, formatted by the sheet. */
  endsAt: string | null;
}

export const useSubscriptionCancel = () => {
  const { t } = useTranslations();
  const formatError = useErrorMessage();
  const [cancelTarget, setCancelTarget] = useState<CancelTarget | null>(null);

  // Status refetches as part of the mutation, so `loading` stays true until
  // the Scheduled panel can show the cancellation: no second click lands.
  const [cancelSubscription, { loading }] = useMutation<
    CancelSubscriptionMutation,
    CancelSubscriptionMutationVariables
  >(CancelSubscriptionDocument, {
    refetchQueries: [{ query: GetSubscriptionStatusDocument }],
    awaitRefetchQueries: true,
  });

  /** Returns whether the subscription is now set to end. */
  const handleCancelConfirm = async (
    reason?: CancellationReason | null,
  ): Promise<boolean> => {
    if (!cancelTarget) return false;
    try {
      const response = await cancelSubscription({
        variables: {
          subscriptionId: cancelTarget.id,
          clientId: cancelTarget.clientId,
          reason: reason ?? null,
        },
      });
      const result = response.data?.cancelSubscription;
      if (result?.success) {
        toast.success(t("userSettings.subscriptionCanceledSuccess"));
        return true;
      }
      toast.error(
        result?.message || t("userSettings.failedToCancelSubscription"),
      );
      return false;
    } catch (error) {
      toast.error(formatError(error));
      return false;
    } finally {
      setCancelTarget(null);
    }
  };

  return {
    loading,
    cancelTarget,
    openCancelSheet: setCancelTarget,
    closeCancelSheet: () => setCancelTarget(null),
    handleCancelConfirm,
  };
};
