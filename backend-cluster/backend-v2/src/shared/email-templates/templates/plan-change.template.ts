import { renderEmailWrapper } from "../components/email-wrapper";
import { EMAIL_STYLES } from "../components/email-theme";
import { escapeHtml, validateEmailUrl } from "../utils/url-validator";

/** One limit that moves when the change lands, e.g. Ledgers 20 → 5. */
interface PlanChangeLimitLine {
  label: string;
  from: string;
  to: string;
}

export interface PlanChangeEmailParams {
  /** `scheduled` confirms the change; `reminder` comes before it lands. */
  kind: "scheduled" | "reminder";
  /** "Growth · Yearly" */
  currentPlan: string;
  /** "Premium · Yearly" */
  newPlan: string;
  /** "October 17, 2027" */
  effectiveDate: string;
  limitChanges: PlanChangeLimitLine[];
  /** Billing settings, where the change can be undone. */
  billingUrl: string;
}

function copy(params: PlanChangeEmailParams) {
  const { kind, currentPlan, newPlan, effectiveDate } = params;
  return {
    subject:
      kind === "scheduled"
        ? `Your plan changes to ${newPlan} on ${effectiveDate}`
        : `Reminder: your plan changes to ${newPlan} on ${effectiveDate}`,
    heading:
      kind === "scheduled"
        ? "Your plan change is scheduled"
        : "Your plan changes soon",
    lead:
      kind === "scheduled"
        ? `On ${effectiveDate}, your plan changes from ${currentPlan} to ${newPlan}. You keep everything in ${currentPlan} until then, and nothing is charged today.`
        : `On ${effectiveDate}, your plan changes from ${currentPlan} to ${newPlan}, and that renewal is billed at the ${newPlan} price. You keep everything in ${currentPlan} until then.`,
    keep: `Changed your mind? Keep ${currentPlan} from Billing settings any time before the change, and nothing changes.`,
    action: `Keep ${currentPlan}`,
  };
}

export function planChangeEmailSubject(params: PlanChangeEmailParams): string {
  return copy(params).subject;
}

export function renderPlanChangeHtml(params: PlanChangeEmailParams): string {
  const billingUrl = validateEmailUrl(params.billingUrl);
  const text = copy(params);
  const limits = params.limitChanges.length
    ? `
    <div class="email-callout" style="${EMAIL_STYLES.callout}">
      <p class="email-callout-title" style="${EMAIL_STYLES.calloutTitle}">
        What changes on ${escapeHtml(params.effectiveDate)}
      </p>
      ${params.limitChanges
        .map(
          (line) => `
      <p class="email-muted" style="margin: 0 0 6px; ${EMAIL_STYLES.mutedText}">
        ${escapeHtml(line.label)}: ${escapeHtml(line.from)} → ${escapeHtml(line.to)}
      </p>`,
        )
        .join("")}
      <p class="email-muted" style="margin: 8px 0 0; ${EMAIL_STYLES.mutedText}">
        Nothing is deleted. A lower limit only stops you going past it.
      </p>
    </div>`
    : "";

  const content = `
    <h2 class="email-heading" style="${EMAIL_STYLES.heading}">${escapeHtml(text.heading)}</h2>

    <p class="email-body-copy" style="${EMAIL_STYLES.paragraph}">
      ${escapeHtml(text.lead)}
    </p>
    ${limits}
    <p class="email-body-copy" style="${EMAIL_STYLES.paragraph}">
      ${escapeHtml(text.keep)}
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

export function renderPlanChangeText(params: PlanChangeEmailParams): string {
  const text = copy(params);
  const limits = params.limitChanges.length
    ? `\nWhat changes on ${params.effectiveDate}:\n${params.limitChanges
        .map((line) => `- ${line.label}: ${line.from} → ${line.to}`)
        .join(
          "\n",
        )}\nNothing is deleted. A lower limit only stops you going past it.\n`
    : "";
  return `
Beancount.io
================

${text.heading}

${text.lead}
${limits}
${text.keep}

${params.billingUrl}

--
Powered by Beancount.io
  `.trim();
}
