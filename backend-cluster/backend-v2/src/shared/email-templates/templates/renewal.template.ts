import { renderEmailWrapper } from "../components/email-wrapper";
import { EMAIL_STYLES } from "../components/email-theme";
import { escapeHtml, validateEmailUrl } from "../utils/url-validator";

interface RenewalEmailBase {
  /** "Premium · Yearly" */
  plan: string;
  /** Billing settings: the card, the plan and cancellation live there. */
  billingUrl: string;
}

/**
 * `failed`: a renewal's first charge failed; `nextAttemptDate` is null when
 * Stripe has scheduled no retry.
 * `final`: the subscription was canceled because the renewal went unpaid.
 * `upcoming`: a yearly plan renews soon.
 * `amount` is a formatted charge, such as "$143.88".
 */
export type RenewalEmailParams =
  | (RenewalEmailBase & {
      kind: "failed";
      amount: string;
      nextAttemptDate: string | null;
    })
  | (RenewalEmailBase & { kind: "final" })
  | (RenewalEmailBase & {
      kind: "upcoming";
      amount: string;
      renewalDate: string;
    });

function copy(params: RenewalEmailParams) {
  const { plan } = params;
  switch (params.kind) {
    case "failed": {
      const charge = `We couldn't charge ${params.amount} for your ${plan} renewal.`;
      return {
        subject: `Your ${plan} renewal didn't go through`,
        heading: "Your renewal didn't go through",
        ...(params.nextAttemptDate
          ? {
              lead: `${charge} You keep ${plan} while we retry automatically, and the next attempt is on ${params.nextAttemptDate}.`,
              next: "Update your card in Billing settings before then to keep your plan. If every retry fails, the plan ends and your account moves to the Free plan.",
            }
          : {
              lead: `${charge} You keep ${plan} for now.`,
              next: "Update your card in Billing settings so we can collect it and keep your plan.",
            }),
        action: "Update your card",
      };
    }
    case "final":
      return {
        subject: `Your ${plan} plan has ended`,
        heading: "We couldn't renew your plan",
        lead: `We couldn't collect payment for your ${plan} renewal, so the plan has ended and your account is on the Free plan.`,
        next: `Nothing in your ledgers is deleted; Free limits only stop you going past them. To get ${plan} back, choose it again in Billing settings.`,
        action: "Choose a plan",
      };
    case "upcoming":
      return {
        subject: `Your ${plan} plan renews on ${params.renewalDate}`,
        heading: "Your plan renews soon",
        lead: `On ${params.renewalDate}, your ${plan} plan renews for another year, and ${params.amount} is charged to your card on file.`,
        next: `Nothing to do if you'd like to keep it. To switch plans or cancel, visit Billing settings before ${params.renewalDate}.`,
        action: "Manage your plan",
      };
  }
}

export function renewalEmailSubject(params: RenewalEmailParams): string {
  return copy(params).subject;
}

export function renderRenewalHtml(params: RenewalEmailParams): string {
  const billingUrl = validateEmailUrl(params.billingUrl);
  const text = copy(params);
  const content = `
    <h2 class="email-heading" style="${EMAIL_STYLES.heading}">${escapeHtml(text.heading)}</h2>

    <p class="email-body-copy" style="${EMAIL_STYLES.paragraph}">
      ${escapeHtml(text.lead)}
    </p>

    <p class="email-body-copy" style="${EMAIL_STYLES.paragraph}">
      ${escapeHtml(text.next)}
    </p>

    <table role="presentation" class="email-action-row" width="100%" cellpadding="0" cellspacing="0" border="0" style="${EMAIL_STYLES.actionRow}">
      <tr>
        <td align="center">
          <a class="email-action" href="${billingUrl}" style="${EMAIL_STYLES.primaryAction}">${escapeHtml(text.action)}</a>
        </td>
      </tr>
    </table>
  `;

  return renderEmailWrapper({
    title: `${text.heading} - Beancount.io`,
    productName: "Beancount.io",
    content,
  });
}

export function renderRenewalText(params: RenewalEmailParams): string {
  const text = copy(params);
  return `
Beancount.io
================

${text.heading}

${text.lead}

${text.next}

${text.action}: ${params.billingUrl}

--
Powered by Beancount.io
  `.trim();
}
