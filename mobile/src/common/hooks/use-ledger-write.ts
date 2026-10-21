import { useCallback } from "react";
import { useRouter } from "expo-router";
import { haptics } from "@/common/haptics";
import { useToast } from "@/common/hooks/use-toast";
import { describeLedgerRefusal } from "@/common/ledger-refusal";
import { i18n } from "@/translations";
import {
  runLedgerWrite,
  type LedgerWriteOutcome,
  type LedgerWriteSpec,
} from "@/common/ledger-write";
import { useIsHere } from "@/common/hooks/use-is-here";

/**
 * Binds `runLedgerWrite` to this app's toast, haptics and router.
 *
 * Screens get one call for the whole confirm-and-return sequence; the branching
 * itself stays in `common/ledger-write.ts`, which imports none of these and is
 * therefore reachable from the unit-test runner.
 */
export const useLedgerWrite = () => {
  const toast = useToast();
  const router = useRouter();
  const isHere = useIsHere();

  return useCallback(
    <T>(spec: LedgerWriteSpec<T>): Promise<LedgerWriteOutcome> =>
      runLedgerWrite(
        {
          showToast: (message, type) => toast.showToast({ message, type }),
          haptics,
          // Only if the user is still on the screen that wrote (w21/194).
          goBack: () => {
            if (isHere()) router.back();
          },
          describeRefusal: (error) => describeLedgerRefusal(error, i18n),
        },
        spec,
      ),
    [toast, router, isHere],
  );
};
