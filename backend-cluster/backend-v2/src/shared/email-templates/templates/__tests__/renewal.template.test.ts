import {
  renewalEmailSubject,
  renderRenewalHtml,
  renderRenewalText,
  type RenewalEmailParams,
} from "../renewal.template";

const base = {
  plan: "Premium · Yearly",
  amount: "$143.88",
  billingUrl: "https://beancount.io/settings/billing",
};
const failed: RenewalEmailParams = {
  ...base,
  kind: "failed",
  nextAttemptDate: "October 22, 2026",
};
const final: RenewalEmailParams = { ...base, kind: "final" };
const upcoming: RenewalEmailParams = {
  ...base,
  kind: "upcoming",
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

  it("gives the amount, the date that matters and the way to Billing, in HTML and text", () => {
    for (const [params, date, action] of [
      [failed, "October 22, 2026", "Update your card"],
      [final, "Free plan", "Choose a plan"],
      [upcoming, "October 17, 2027", "Manage your plan"],
    ] as const) {
      const html = renderRenewalHtml(params);
      const text = renderRenewalText(params);
      for (const body of [html, text]) {
        expect(body).toContain("$143.88");
        expect(body).toContain(date);
        expect(body).toContain(action);
      }
      expect(html).toContain('href="https://beancount.io/settings/billing"');
      expect(text).toContain("https://beancount.io/settings/billing");
    }
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
