import {
  PaymentType,
  SubscriptionTier,
  SUBSCRIPTION_CONFIG,
  StripeClientConfig,
} from "../stripe";

describe("Stripe Configuration", () => {
  describe("PaymentType enum", () => {
    it("should define RECURRING type", () => {
      expect(PaymentType.RECURRING).toBe("subscription");
    });

    it("should define ONE_OFF type", () => {
      expect(PaymentType.ONE_OFF).toBe("payment");
    });
  });

  describe("SUBSCRIPTION_CONFIG", () => {
    describe("beancount-web-prod configuration", () => {
      let prodConfig: StripeClientConfig;

      beforeEach(() => {
        prodConfig = SUBSCRIPTION_CONFIG["beancount-web-prod"];
      });

      it("should have production configuration", () => {
        expect(prodConfig).toBeDefined();
      });

      it("should have correct product IDs", () => {
        expect(prodConfig.productIds).toEqual([
          "prod_LrLIJaWkCbz2uA",
          "prod_TwIDs5ys1JPw89",
          "prod_TwIDr09gy8HuYy",
        ]);
      });

      it("should have all plan IDs", () => {
        expect(prodConfig.planIds).toEqual([
          "price_1L9ccEEqsEqs2tLVKPRV17wb", // Legacy $9.99
          "price_1L9ccEEqsEqs2tLVbeBgHm9p", // Legacy $99.99 yearly
          "price_1RrSOGEqsEqs2tLVFnyB34qG", // Premium $14.99
          "price_1US5htEqsEqs2tLVENCzLaZB", // Premium yearly $143.88
          "price_1SyPdaEqsEqs2tLViLPUDoVi", // Growth monthly $99.99
          "price_1SyPdbEqsEqs2tLV7PJyWZed", // Growth yearly $959.88
          "price_1SyPdcEqsEqs2tLVCWEgU1PZ", // Organization monthly $499.99
          "price_1SyPdfEqsEqs2tLVmK6zCrP6", // Organization yearly $4,799.88
        ]);
      });

      it("should have eight subscription plans", () => {
        expect(prodConfig.plans).toHaveLength(8);
      });

      it("offers Premium yearly at $143.88 and keeps both older Premium prices billable but retired", () => {
        const plan = (priceId: string) =>
          prodConfig.plans.find((p) => p.priceId === priceId);
        expect(plan("price_1US5htEqsEqs2tLVENCzLaZB")).toMatchObject({
          tier: SubscriptionTier.PREMIUM,
          interval: "year",
        });
        expect(plan("price_1US5htEqsEqs2tLVENCzLaZB")).not.toHaveProperty(
          "retired",
        );
        for (const legacy of [
          "price_1L9ccEEqsEqs2tLVKPRV17wb",
          "price_1L9ccEEqsEqs2tLVbeBgHm9p",
        ]) {
          expect(plan(legacy)).toMatchObject({
            tier: SubscriptionTier.PREMIUM,
            retired: true,
          });
        }
        // One offered price per tier and cycle, so a change has one target.
        const offered = prodConfig.plans
          .filter((p) => !p.retired)
          .map((p) => `${p.tier}:${p.interval}`);
        expect(new Set(offered).size).toBe(offered.length);
      });

      it("pins every portal session to the billing-only portal configuration", () => {
        expect(prodConfig.portalConfigurationId).toBe(
          "bpc_1US5i0EqsEqs2tLVVF907WfA",
        );
      });

      it("should have monthly basic plan", () => {
        const monthlyBasic = prodConfig.plans.find(
          (p) => p.priceId === "price_1L9ccEEqsEqs2tLVKPRV17wb",
        );
        expect(monthlyBasic).toBeDefined();
        expect(monthlyBasic?.type).toBe(PaymentType.RECURRING);
        expect(monthlyBasic?.description).toContain("Monthly");
        expect(monthlyBasic?.description).toContain("$9.99");
      });

      it("should have yearly basic plan", () => {
        const yearlyBasic = prodConfig.plans.find(
          (p) => p.priceId === "price_1L9ccEEqsEqs2tLVbeBgHm9p",
        );
        expect(yearlyBasic).toBeDefined();
        expect(yearlyBasic?.type).toBe(PaymentType.RECURRING);
        expect(yearlyBasic?.description).toContain("Yearly");
        expect(yearlyBasic?.description).toContain("$99.99");
      });

      it("should have monthly premium plan", () => {
        const monthlyPremium = prodConfig.plans.find(
          (p) => p.priceId === "price_1RrSOGEqsEqs2tLVFnyB34qG",
        );
        expect(monthlyPremium).toBeDefined();
        expect(monthlyPremium?.type).toBe(PaymentType.RECURRING);
        expect(monthlyPremium?.description).toContain("Premium");
        expect(monthlyPremium?.description).toContain("$14.99");
      });

      it("should have correct URLs", () => {
        expect(prodConfig.successUrl).toBe(
          "https://beancount.io/pricing/?success=true",
        );
        expect(prodConfig.cancelUrl).toBe("https://beancount.io/pricing");
        expect(prodConfig.webhook).toBe(
          "https://beancount.io/api-gateway/stripe/webhook",
        );
      });

      it("should have secrets from config", () => {
        // These should be from config (which reads from environment variables)
        expect(prodConfig.webhookSecret).toBeDefined();
        expect(prodConfig.stripePubKey).toBeDefined();
        expect(prodConfig.stripePriKey).toBeDefined();
        // Values should be strings (even if empty)
        expect(typeof prodConfig.webhookSecret).toBe("string");
        expect(typeof prodConfig.stripePubKey).toBe("string");
        expect(typeof prodConfig.stripePriKey).toBe("string");
      });
    });

    describe("configuration structure validation", () => {
      it("should expose only the supported live billing client", () => {
        const clients = Object.keys(SUBSCRIPTION_CONFIG);
        expect(clients).toHaveLength(1);
        expect(clients).toContain("beancount-web-prod");
        expect(clients).not.toContain("beancount-web-dev");
      });

      it("should have consistent structure across all clients", () => {
        Object.values(SUBSCRIPTION_CONFIG).forEach((config) => {
          expect(config).toHaveProperty("productIds");
          expect(config).toHaveProperty("planIds");
          expect(config).toHaveProperty("plans");
          expect(config).toHaveProperty("webhookSecret");
          expect(config).toHaveProperty("stripePubKey");
          expect(config).toHaveProperty("stripePriKey");
          expect(config).toHaveProperty("successUrl");
          expect(config).toHaveProperty("cancelUrl");
          expect(config).toHaveProperty("webhook");
        });
      });

      it("should have matching plan IDs in planIds and plans arrays", () => {
        Object.values(SUBSCRIPTION_CONFIG).forEach((config) => {
          const planIdsFromPlans = config.plans.map((p) => p.priceId);
          expect(planIdsFromPlans.sort()).toEqual(config.planIds.sort());
        });
      });

      it("should only use RECURRING payment type in all plans", () => {
        Object.values(SUBSCRIPTION_CONFIG).forEach((config) => {
          config.plans.forEach((plan) => {
            expect(plan.type).toBe(PaymentType.RECURRING);
          });
        });
      });
    });
  });
});
