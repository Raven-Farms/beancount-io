import { eq } from "drizzle-orm";
import type { DbExecutor } from "@/drizzle/drizzle";
import { reportedPurchases } from "./schema";
import type { IReportedPurchaseModel } from "./types";

export class ReportedPurchasePostgresModel implements IReportedPurchaseModel {
  async claim(db: DbExecutor, invoiceId: string): Promise<boolean> {
    const rows = await db
      .insert(reportedPurchases)
      .values({ invoiceId })
      .onConflictDoNothing()
      .returning({ invoiceId: reportedPurchases.invoiceId });
    return rows.length > 0;
  }

  async release(db: DbExecutor, invoiceId: string): Promise<void> {
    await db
      .delete(reportedPurchases)
      .where(eq(reportedPurchases.invoiceId, invoiceId));
  }
}
