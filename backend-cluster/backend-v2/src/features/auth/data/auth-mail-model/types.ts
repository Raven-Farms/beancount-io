import type { InferSelectModel } from "drizzle-orm";
import type { DbExecutor } from "@/drizzle/drizzle";
import type { authMail } from "./schema";

export type AuthMail = InferSelectModel<typeof authMail>;
export type AuthMailKind = AuthMail["kind"];
export interface IAuthMailModel {
  enqueue(
    db: DbExecutor,
    mail: Pick<AuthMail, "id" | "kind" | "payload" | "expiresAt">,
  ): Promise<void>;
  claim(db: DbExecutor): Promise<AuthMail | null>;
  savePayload(
    db: DbExecutor,
    mail: AuthMail,
    payload: string,
  ): Promise<boolean>;
  complete(db: DbExecutor, mail: AuthMail): Promise<void>;
  retry(db: DbExecutor, mail: AuthMail): Promise<void>;
  cleanup(db: DbExecutor): Promise<void>;
}
