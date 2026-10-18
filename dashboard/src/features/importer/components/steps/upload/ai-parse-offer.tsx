import { FileQuestion, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/common/components/ui/card";
import { Button } from "@/common/components/ui/button";
import { useTranslations } from "@/common/hooks/use-translations";

/**
 * A CSV the client could not read. AI parsing spends the account's AI
 * tokens, so it is a choice the user makes, never a silent fallback.
 */
export function AiParseOffer({
  fileName,
  onParseWithAi,
  onReset,
}: {
  fileName: string;
  onParseWithAi: () => void;
  onReset: () => void;
}) {
  const { t } = useTranslations();
  return (
    <Card>
      <CardContent className="py-2">
        <div className="mx-auto flex max-w-md flex-col items-center space-y-6 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <FileQuestion className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-foreground">
              {t("importer.aiOffer.title")}
            </h3>
            {fileName && (
              <p className="break-all font-mono text-xs text-muted-foreground">
                {fileName}
              </p>
            )}
            <p className="text-sm text-muted-foreground">
              {t("importer.aiOffer.description")}
            </p>
          </div>
          <div className="flex w-full flex-col gap-2 sm:flex-row">
            <Button
              variant="outline"
              className="flex-1"
              size="sm"
              onClick={onReset}
            >
              {t("importer.error.uploadDifferentFile")}
            </Button>
            <Button className="flex-1" size="sm" onClick={onParseWithAi}>
              <Sparkles className="mr-2 h-4 w-4" />
              {t("importer.aiOffer.parseWithAi")}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
