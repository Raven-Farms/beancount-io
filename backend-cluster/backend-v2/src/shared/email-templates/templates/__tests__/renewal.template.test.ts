import {
  renewalEmailSubject,
  renderRenewalHtml,
  renderRenewalText,
  type RenewalEmailParams,
} from "../renewal.template";

const base = {
  plan: "Premium · Yearly",
  billingUrl: "https://beancount.io/settings/billing",
};
const failed: RenewalEmailParams = {
  ...base,
  kind: "failed",
  amount: "$143.88",
  nextAttemptDate: "October 22, 2026",
};
const unscheduled: RenewalEmailParams = { ...failed, nextAttemptDate: null };
const final: RenewalEmailParams = { ...base, kind: "final" };
const upcoming: RenewalEmailParams = {
  ...base,
  kind: "upcoming",
  amount: "$143.88",
  renewalDate: "October 17, 2027",
};

describe("renewal email", () => {
  it("names the plan in every kind's subject", () => {
    expect(renewalEmailSubject(failed)).toBe(
      "Your Premium · Yearly renewal didn't go through",
    );
    expect(renewalEmailSubject(final)).toBe(
      "Your Premium · Yearly plan has ended",
    );
    expect(renewalEmailSubject(upcoming)).toBe(
      "Your Premium · Yearly plan renews on October 17, 2027",
    );
  });

  it("gives what matters and the way to Billing, in HTML and text", () => {
    for (const [params, facts, action] of [
      [failed, ["$143.88", "October 22, 2026"], "Update your card"],
      [unscheduled, ["$143.88", "over the coming weeks"], "Update your card"],
      [final, ["the plan has ended", "Free plan"], "Choose a plan"],
      [upcoming, ["$143.88", "October 17, 2027"], "Manage your plan"],
    ] as const) {
      const html = renderRenewalHtml(params);
      const text = renderRenewalText(params);
      for (const body of [html, text]) {
        for (const fact of facts) expect(body).toContain(fact);
        expect(body).toContain(action);
      }
      expect(html).toContain('href="https://beancount.io/settings/billing"');
      expect(text).toContain("https://beancount.io/settings/billing");
    }
  });

  it("names no retry date when the failure gives none", () => {
    const text = renderRenewalText(unscheduled);

    expect(text).toContain(
      "We'll keep retrying automatically over the coming weeks, and you keep Premium · Yearly meanwhile.",
    );
    expect(text).not.toContain("next attempt");
  });

  it("escapes every value it puts into HTML", () => {
    const html = renderRenewalHtml({
      ...failed,
      plan: '<script>alert("x")</script>',
    });
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
  });

  it("refuses a link that is not a safe web address", () => {
    expect(() =>
      renderRenewalHtml({ ...upcoming, billingUrl: "javascript:alert(1)" }),
    ).toThrow();
  });
});
