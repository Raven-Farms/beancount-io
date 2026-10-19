import { renderEmailWrapper } from "../components/email-wrapper";
import { EMAIL_STYLES } from "../components/email-theme";
import { escapeHtml, validateEmailUrl } from "../utils/url-validator";

interface RenewalEmailBase {
  /** "Premium · Yearly" */
  plan: string;
  /** "$143.88" */
  amount: string;
  /** Billing settings: the card, the plan and cancellation live there. */
  billingUrl: string;
}

/**
 * `failed`: a renewal's first charge failed and Stripe will retry.
 * `final`: the last retry failed, so the subscription was canceled.
 * `upcoming`: a yearly plan renews soon.
 */
export type RenewalEmailParams =
  | (RenewalEmailBase & { kind: "failed"; nextAttemptDate: string })
  | (RenewalEmailBase & { kind: "final" })
  | (RenewalEmailBase & { kind: "upcoming"; renewalDate: string });

function copy(params: RenewalEmailParams) {
  const { plan, amount } = params;
  switch (params.kind) {
    case "failed":
      return {
        subject: `Your ${plan} renewal didn't go through`,
        heading: "Your renewal didn't go through",
        lead: `We couldn't charge ${amount} for your ${plan} renewal. You keep ${plan} while we retry automatically, and the next attempt is on ${params.nextAttemptDate}.`,
        next: "Update your card in Billing settings before then to keep your plan. If every retry fails, the plan ends and your account moves to the Free plan.",
        action: "Update your card",
      };
    case "final":
      return {
        subject: `Your ${plan} plan has ended`,
        heading: "We couldn't renew your plan",
        lead: `The last attempt to charge ${amount} for your ${plan} renewal failed, so the plan has ended and your account is on the Free plan.`,
        next: `Nothing is deleted. Free limits only stop you going past them. To get ${plan} back, choose it again in Billing settings.`,
        action: "Choose a plan",
      };
    case "upcoming":
      return {
        subject: `Your ${plan} plan renews on ${params.renewalDate}`,
        heading: "Your plan renews soon",
        lead: `On ${params.renewalDate}, your ${plan} plan renews for another year, and ${amount} is charged to your card on file.`,
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
