import { eq } from "drizzle-orm";
import type { DbExecutor } from "@/drizzle/drizzle";
import { sentBillingEmails } from "./schema";
import type { ISentBillingEmailModel } from "./types";

export class SentBillingEmailPostgresModel implements ISentBillingEmailModel {
  async claim(db: DbExecutor, key: string): Promise<boolean> {
    const rows = await db
      .insert(sentBillingEmails)
      .values({ key })
      .onConflictDoNothing()
      .returning({ key: sentBillingEmails.key });
    return rows.length > 0;
  }

  async release(db: DbExecutor, key: string): Promise<void> {
    await db.delete(sentBillingEmails).where(eq(sentBillingEmails.key, key));
  }
}
