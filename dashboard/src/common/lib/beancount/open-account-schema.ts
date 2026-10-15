import { z } from "zod";
import { accountTokenProblem, type AccountTokenProblem } from "./account-token";

export function buildOpenAccountSchema(
  prefixes: string[],
  messages: {
    required: string;
    mustStartWith: string;
    /** Message for each reason the name is not a complete account token. */
    invalid: (problem: AccountTokenProblem) => string;
  },
) {
  return z.object({
    date: z.date(),
    account: z
      .string()
      .min(1, messages.required)
      .refine(
        (val) =>
          prefixes.length === 0 ||
          prefixes.some((prefix) => val.startsWith(`${prefix}:`)),
        messages.mustStartWith,
      )
      .superRefine((val, ctx) => {
        const problem = accountTokenProblem(val);
        if (problem) {
          ctx.addIssue({ code: "custom", message: messages.invalid(problem) });
        }
      }),
  });
}

/**
 * The localized message for each `AccountTokenProblem`, shared by the Accounts
 * dialog and the Journal "Account" tab so both name the same reason.
 */
export function accountProblemMessage(
  t: (key: string, params?: Record<string, string>) => string,
): (problem: AccountTokenProblem) => string {
  return (problem) => {
    switch (problem.kind) {
      case "whitespace":
        return t("page.accounts.accountNameWhitespace");
      case "empty-component":
        return t("page.accounts.accountNameEmptyComponent");
      case "component-start":
        return t("page.accounts.accountNameComponentStart", {
          component: problem.component,
        });
      case "invalid-character":
        return t("page.accounts.accountNameInvalidCharacter", {
          component: problem.component,
        });
      default:
        return t("page.accounts.accountNameInvalid");
    }
  };
}
