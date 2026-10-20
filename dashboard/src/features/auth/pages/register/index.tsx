import { useState } from "react";
import { useSearch } from "@tanstack/react-router";
import RegisterPage from "./register";
import SignUpOtpPage from "./register-otp";
import { useAuthProviders } from "@/features/auth/hooks/use-auth-providers";
import { useTranslations } from "@/common/hooks/use-translations";
import { getSafeRedirectPath } from "@/common/lib/auth/auth";
import { AuthPageLayout } from "@/features/auth/components/auth-page-layout";
import { GoogleSignInButton } from "@/features/auth/components/google-sign-in-button";

type RegistrationStep = "register" | "otp";

type RegistrationData = {
  sessionId: string;
  email: string;
};

/**
 * Parent component that manages the registration flow
 * Handles state-based page switching between registration form and OTP verification
 */
export default function RegisterFlow() {
  const search = useSearch({ from: "/auth/sign-up" });
  const [step, setStep] = useState<RegistrationStep>("register");
  const [registrationData, setRegistrationData] =
    useState<RegistrationData | null>(null);
  const { password: passwordEnabled } = useAuthProviders();
  const { t } = useTranslations();

  // Handle successful registration form submission
  const handleRegisterSuccess = (sessionId: string, email: string) => {
    setRegistrationData({ sessionId, email });
    setStep("otp");
  };

  // Handle successful OTP verification
  const handleOtpSuccess = () => {
    // Navigation to welcome page will be handled by SignUpOtpPage
    // This component just manages the flow state
  };

  // Handle going back to registration form
  const handleBackToRegister = () => {
    setStep("register");
    setRegistrationData(null);
  };

  // AUTH_PASSWORD_ENABLED=false: accounts are created by continuing with
  // Google (subject to the server's signup allowlist).
  if (!passwordEnabled) {
    return (
      <AuthPageLayout>
        <div className="space-y-6">
          <p className="text-muted-foreground">{t("auth.googleOnlySignUp")}</p>
          <GoogleSignInButton next={getSafeRedirectPath(search.next) ?? "/"} />
        </div>
      </AuthPageLayout>
    );
  }

  if (step === "otp" && registrationData) {
    return (
      <SignUpOtpPage
        sessionId={registrationData.sessionId}
        email={registrationData.email}
        next={search.next}
        onSuccess={handleOtpSuccess}
        onBack={handleBackToRegister}
      />
    );
  }

  return (
    <RegisterPage
      withDefaultLedger={search.withDefaultLedger ?? false}
      inviteSrc={search.src}
      inviteBy={search.by}
      onSuccess={handleRegisterSuccess}
    />
  );
}
