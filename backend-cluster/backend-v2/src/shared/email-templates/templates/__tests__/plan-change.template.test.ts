import {
  planChangeEmailSubject,
  renderPlanChangeHtml,
  renderPlanChangeText,
  type PlanChangeEmailParams,
} from "../plan-change.template";

const params: PlanChangeEmailParams = {
  kind: "scheduled",
  currentPlan: "Growth · Yearly",
  newPlan: "Premium · Yearly",
  effectiveDate: "October 17, 2027",
  limitChanges: [{ label: "Ledgers", from: "20", to: "5" }],
  billingUrl: "https://beancount.io/settings/billing",
};

describe("plan change email", () => {
  it("names the change in both kinds' subjects", () => {
    expect(planChangeEmailSubject(params)).toBe(
      "Your plan changes to Premium · Yearly on October 17, 2027",
    );
    expect(planChangeEmailSubject({ ...params, kind: "reminder" })).toBe(
      "Reminder: your plan changes to Premium · Yearly on October 17, 2027",
    );
  });

  it("says what changes and how to keep the current plan, in HTML and text", () => {
    const html = renderPlanChangeHtml(params);
    const text = renderPlanChangeText(params);
    for (const body of [html, text]) {
      expect(body).toContain("October 17, 2027");
      expect(body).toContain("20 → 5");
      expect(body).toContain("Nothing is deleted.");
    }
    expect(html).toContain('href="https://beancount.io/settings/billing"');
    expect(html).toContain("Keep Growth · Yearly");
    expect(text).toContain("https://beancount.io/settings/billing");
  });

  it("leaves out the limits block when no limit moves", () => {
    expect(renderPlanChangeText({ ...params, limitChanges: [] })).not.toContain(
      "What changes on",
    );
  });

  it("escapes every value it puts into HTML", () => {
    const html = renderPlanChangeHtml({
      ...params,
      newPlan: '<script>alert("x")</script>',
    });
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
  });

  it("refuses a link that is not a safe web address", () => {
    expect(() =>
      renderPlanChangeHtml({ ...params, billingUrl: "javascript:alert(1)" }),
    ).toThrow();
  });
});
