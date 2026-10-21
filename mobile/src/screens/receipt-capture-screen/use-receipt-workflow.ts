import { useState, useCallback, useRef } from "react";
import * as FileSystem from "expo-file-system/legacy";
import {
  useGenerateTempAssetUploadUrlMutation,
  useParseReceiptMutation,
} from "@/generated-graphql/graphql";
import { receiptDate, parseErrorCode } from "./receipt-utils";
import { captureError } from "@/common/sentry/capture";
import { createIdleGuard, uploadPercent } from "./upload-guard";

/** An upload may stall this long between progress events before it fails. */
const UPLOAD_IDLE_MS = 30_000;

type ParsedReceipt = {
  date: string;
  payee: string;
  description: string;
  amount: number;
  sourceAccount: string;
  targetAccount: string;
};

type ReceiptPhase =
  | { kind: "idle" }
  | { kind: "uploading"; percent: number | null }
  | { kind: "parsing" }
  | ({ kind: "parsed" } & ParsedReceipt)
  | { kind: "error"; message: string };

export type ReceiptWorkflow = {
  phase: ReceiptPhase;
  startCapture: (
    uri: string,
    mimeType: string,
    filename: string,
    ledgerId: string,
  ) => Promise<void>;
  /** Abandon the attempt in flight and return to the preview (w21/205). */
  cancel: () => void;
  reset: () => void;
};

/** One run of the workflow; `cancel` flips it and aborts what is in flight. */
type Attempt = {
  cancelled: boolean;
  abort: AbortController;
  upload: { cancelAsync: () => Promise<void> } | null;
};

export const useReceiptWorkflow = (): ReceiptWorkflow => {
  const [phase, setPhase] = useState<ReceiptPhase>({ kind: "idle" });

  const attempt = useRef<Attempt | null>(null);

  const [generateUploadUrl] = useGenerateTempAssetUploadUrlMutation();
  const [parseReceipt] = useParseReceiptMutation();

  const startCapture = useCallback(
    async (
      uri: string,
      mimeType: string,
      filename: string,
      ledgerId: string,
    ) => {
      const run: Attempt = {
        cancelled: false,
        abort: new AbortController(),
        upload: null,
      };
      attempt.current = run;
      // A cancelled attempt finishes silently: its late results and errors
      // must not move a screen the user already left.
      const live = () => !run.cancelled;
      try {
        setPhase({ kind: "uploading", percent: null });

        // 1. Get presigned upload URL (30s timeout — Apollo has no built-in timeout)
        const urlResult = await Promise.race([
          generateUploadUrl({
            variables: { mimeType, filename },
            context: { fetchOptions: { signal: run.abort.signal } },
          }),
          new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error("upload_url_timeout")), 30_000),
          ),
        ]);
        if (!live()) return;
        const uploadData = urlResult.data?.generateTempAssetUploadUrl;
        if (!uploadData) throw new Error("upload_url_failed");

        // 2. PUT image to S3 via presigned URL
        // expo-file-system handles Content-Length automatically — plain fetch with
        // a Blob body omits it, causing S3 to hang indefinitely.
        // The limit is idle time, not the whole transfer: a slow link that
        // keeps moving bytes finishes, a stalled one fails (w21/205).
        let timedOut = false;
        const idle = createIdleGuard(UPLOAD_IDLE_MS, () => {
          timedOut = true;
          void run.upload?.cancelAsync();
        });
        let lastPercent: number | null = null;
        const task = FileSystem.createUploadTask(
          uploadData.uploadUrl,
          uri,
          {
            httpMethod: "PUT",
            headers: { "Content-Type": mimeType },
            uploadType: FileSystem.FileSystemUploadType.BINARY_CONTENT,
          },
          (progress) => {
            idle.touch();
            const percent = uploadPercent(progress);
            if (percent !== lastPercent && live()) {
              lastPercent = percent;
              setPhase({ kind: "uploading", percent });
            }
          },
        );
        run.upload = task;
        idle.touch();
        let uploadResult: Awaited<ReturnType<typeof task.uploadAsync>>;
        try {
          uploadResult = await task.uploadAsync();
        } finally {
          idle.stop();
        }
        if (!live()) return;
        if (timedOut) throw new Error("upload_s3_timeout");
        if (
          !uploadResult ||
          uploadResult.status < 200 ||
          uploadResult.status >= 300
        ) {
          throw new Error("upload_failed");
        }

        // 3. Parse receipt with LLM. Under Apollo's default errorPolicy a
        // GraphQL error rejects here rather than populating `result.errors`;
        // classify the leg from the thrown ApolloError so quota exhaustion and
        // parse failures show their own messages instead of "Upload failed".
        setPhase({ kind: "parsing" });
        let parseResult: Awaited<ReturnType<typeof parseReceipt>>;
        try {
          parseResult = await parseReceipt({
            variables: { s3ObjectKey: uploadData.objectKey, ledgerId },
            context: { fetchOptions: { signal: run.abort.signal } },
          });
        } catch (parseErr) {
          if (!live()) return;
          captureError(parseErr, { phase: "parse", ledgerId });
          throw new Error(parseErrorCode(parseErr));
        }

        if (!live()) return;
        const parsed = parseResult.data?.parseReceipt;
        if (!parsed) throw new Error("parse_failed");

        // The uploaded asset is only an LLM input — it expires out of the temp
        // bucket on its own. Nothing downstream needs the objectKey because the
        // transaction is written through the generic addEntries mutation.
        setPhase({
          kind: "parsed",
          date: receiptDate(parsed.date),
          payee: parsed.payee,
          description: parsed.description,
          amount: parsed.amount,
          sourceAccount: parsed.sourceAccount ?? "",
          targetAccount: parsed.targetAccount ?? "",
        });
      } catch (err: unknown) {
        if (!live()) return;
        const msg = err instanceof Error ? err.message : "upload_failed";
        // Parse-leg errors are already captured with their phase above; capture
        // anything else (upload-URL mint, S3 PUT, network) here so the real
        // cause is never swallowed — the screen only shows a generic message.
        if (msg !== "quota_exhausted" && msg !== "parse_failed") {
          captureError(err, { phase: "upload", code: msg });
        }
        setPhase({ kind: "error", message: msg });
      }
    },
    [generateUploadUrl, parseReceipt],
  );

  const cancel = useCallback(() => {
    const run = attempt.current;
    if (run) {
      run.cancelled = true;
      run.abort.abort();
      void run.upload?.cancelAsync().catch(() => undefined);
    }
    setPhase({ kind: "idle" });
  }, []);

  const reset = useCallback(() => setPhase({ kind: "idle" }), []);

  return { phase, startCapture, cancel, reset };
};
