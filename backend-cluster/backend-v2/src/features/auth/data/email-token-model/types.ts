// Database-agnostic type (no mongoose dependencies)
export interface EmailToken {
  token: string;
  userId: string;
  expireAt: string;
}

// Database-agnostic interface
export interface IEmailTokenModel {
  regenerateToken(userId: string): Promise<EmailToken>;
  /** Idempotently issue a durable-mail token without invalidating earlier links. */
  issueToken(
    userId: string,
    token: string,
    expiresAt?: Date,
  ): Promise<EmailToken | null>;
  findOneAndDelete(token: string): Promise<EmailToken | null>;
  findOne(token: string): Promise<EmailToken | null>;
  deleteByUserId(userId: string): Promise<void>;
}
