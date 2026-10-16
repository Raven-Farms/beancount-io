import { useParams } from "@tanstack/react-router";
import { useTranslations } from "@/common/hooks/use-translations";
import { UserProfileHeader } from "../components/user-profile-header";
import { UserProfileUnavailable } from "../components/user-profile-unavailable";

export function UserProfileNotFoundPage() {
  const { username } = useParams({ from: "/ledger/$username" });
  const { t } = useTranslations();
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <UserProfileHeader />
      <main className="flex-1">
        <UserProfileUnavailable username={username} />
      </main>
      <footer className="border-t px-5 py-6 text-center text-xs text-muted-foreground">
        {t("userProfile.footer")}
      </footer>
    </div>
  );
}
