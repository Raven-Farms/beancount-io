import AsyncStorage from "@react-native-async-storage/async-storage";
import { getFormatDate } from "./format-util";

/**
 * The Create Ledger draft, as ADR021's "Resuming" allows it (w21/053).
 *
 * The screen wrote its whole form to persistent storage on every change and
 * removed it only after a successful create, so a typed opening balance sat
 * in plain storage indefinitely, survived sign-out into the next account, and
 * a draft from days ago resumed with its old "Books begin" date. The draft is
 * kept for the creation `requestId`'s 24-hour window — long enough for a
 * retried create to stay idempotent — never holds an amount, is cleared with
 * the rest of the server-scoped state, and a stale Books begin reopens as
 * today.
 */
export const CREATE_LEDGER_DRAFT_KEY = "create-ledger-draft";

/** The server keeps a creation `requestId` for 24 hours (ADR021). */
const DRAFT_LIFETIME_MS = 24 * 60 * 60 * 1000;

export interface CreateLedgerDraft<Values> {
  step: number;
  startKind: string;
  presetId: string | null;
  requestId: string;
  /**
   * When `requestId` was minted. The lifetime runs from here, not from the
   * last save: every keystroke saves, so a draft touched daily kept a
   * requestId the server had long forgotten (w21/066).
   */
  requestedAt?: number;
  /**
   * A fingerprint of the request last sent under `requestId`. A resumed draft
   * has no amount to rebuild that request from, so it carries this instead:
   * the next create is the same request, or it gets an id of its own
   * (w21/434).
   */
  sentFingerprint?: string;
  values: Values;
}

type DraftValues = {
  historyStart: string;
  openingAmount: string;
  openingAccount?: string;
};

/** The step holding the form's fields, the opening amount among them. */
const FORM_STEP = 1;

/** The draft as stored: without the opening amount, with when it was saved. */
export function serializeCreateLedgerDraft<Values extends DraftValues>(
  draft: CreateLedgerDraft<Values>,
  now: Date = new Date(),
): string {
  return JSON.stringify({
    ...draft,
    requestedAt: draft.requestedAt ?? now.getTime(),
    values: { ...draft.values, openingAmount: "" },
    savedAt: now.getTime(),
  });
}

/**
 * The stored draft to resume, or null when there is none, it is malformed,
 * or it has outlived its `requestId`. A draft saved before today reopens with
 * today's Books begin rather than the day it was started. One left past the
 * form with an opening account reopens on the form: its amount is not kept,
 * and Review would build the ledger without the balance (w21/435).
 */
export function restoreCreateLedgerDraft<Values extends DraftValues>(
  raw: string | null,
  now: Date = new Date(),
): CreateLedgerDraft<Values> | null {
  if (!raw) return null;
  let parsed: (CreateLedgerDraft<Values> & { savedAt?: unknown }) | null;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (
    !parsed ||
    typeof parsed.savedAt !== "number" ||
    typeof parsed.requestId !== "string" ||
    !parsed.values ||
    now.getTime() -
      (typeof parsed.requestedAt === "number"
        ? parsed.requestedAt
        : parsed.savedAt) >
      DRAFT_LIFETIME_MS
  ) {
    return null;
  }
  const { savedAt, ...draft } = parsed;
  const today = getFormatDate(now);
  const stale = getFormatDate(new Date(savedAt)) < today;
  const amountLost = Boolean(draft.values.openingAccount);
  return {
    ...draft,
    step: amountLost ? Math.min(draft.step, FORM_STEP) : draft.step,
    values: {
      ...draft.values,
      openingAmount: "",
      ...(stale && { historyStart: today }),
    },
  };
}

/** Forget the draft: on sign-out, on a server change, after a create. */
export async function clearCreateLedgerDraft(): Promise<void> {
  await AsyncStorage.removeItem(CREATE_LEDGER_DRAFT_KEY).catch(() => {});
}
