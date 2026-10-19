// Database-agnostic types (no mongoose dependencies)
export interface PaidCustomer {
  id: string; // Converted from ObjectId to string
  userId: string;
  stripeCustomerId: string;
  clientId: string;
  email?: string;
  name?: string;
  phone?: string;
  currentPeriodEnd?: Date;
  /** Null/absent for historical or otherwise unverified subscription periods. */
  periodVerificationVersion?: number;
  /** The tier the verified period paid for; absent when unverified. */
  periodTier?: string;
  createdAt: Date;
  updatedAt: Date;
  /** Opaque persistence version, retaining database timestamp precision. */
  version?: string;
}

export interface CreatePaidCustomerInput {
  userId: string;
  stripeCustomerId: string;
  clientId: string;
  email?: string;
  name?: string;
  phone?: string;
  currentPeriodEnd?: Date;
}

export interface UpdatePaidCustomerInput {
  email?: string;
  name?: string;
  phone?: string;
  currentPeriodEnd?: Date | null;
  clientId?: string;
  updatedAt?: Date;
}

/**
 * Database executor type - represents any database connection/transaction.
 * This allows the interface to remain database-agnostic while supporting transactions.
 */
type DbExecutor = any;

// Database-agnostic interface
// All methods now accept a DbExecutor as the first parameter to support transactions.
export interface IPaidCustomerModel {
  findByUserIdAndClientId(
    db: DbExecutor,
    userId: string,
    clientId: string,
  ): Promise<PaidCustomer | null>;
  findByStripeCustomerIdAndClientId(
    db: DbExecutor,
    stripeCustomerId: string,
    clientId: string,
  ): Promise<PaidCustomer | null>;
  findByUserIdWithActivePeriod(
    db: DbExecutor,
    userId: string,
  ): Promise<PaidCustomer | null>;
  create(db: DbExecutor, input: CreatePaidCustomerInput): Promise<PaidCustomer>;
  updateCustomerById(
    db: DbExecutor,
    id: string,
    input: UpdatePaidCustomerInput,
  ): Promise<PaidCustomer | null>;
  /** Atomically record a provider-verified period, its tier and verification version. */
  updatePeriodIfUnchanged(
    db: DbExecutor,
    customer: PaidCustomer,
    currentPeriodEnd: Date | null,
    verificationVersion: number,
    tier: string | null,
  ): Promise<boolean>;
  updateByUserIdAndClientId(
    db: DbExecutor,
    userId: string,
    clientId: string,
    input: UpdatePaidCustomerInput,
  ): Promise<{ modifiedCount: number }>;
  findByUserId(db: DbExecutor, userId: string): Promise<PaidCustomer[]>;
  deleteByUserId(db: DbExecutor, userId: string): Promise<void>;
  listWithActivePeriod(
    db: DbExecutor,
    options: { limit: number; offset: number; clientId: string },
  ): Promise<{ users: ActivePaidUser[]; total: number }>;
  countWithActivePeriod(db: DbExecutor): Promise<number>;
}

export interface ActivePaidUser {
  userId: string;
  email: string;
  firstName?: string;
  lastName?: string;
  ledgerUsername: string;
  isBlocked: boolean;
  lastSeenAt?: Date;
  createAt?: Date;
  stripeCustomerId: string;
  currentPeriodEnd: Date;
}
