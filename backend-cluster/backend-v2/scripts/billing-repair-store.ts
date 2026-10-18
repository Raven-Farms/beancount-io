import type { Pool, PoolClient } from "pg";
import {
  fingerprint,
  type BindingSnapshot,
  type RepairStore,
} from "./reconcile-billing-core";
const selectBindings = `SELECT id, user_id AS "userId", client_id AS "clientId", stripe_customer_id AS "stripeCustomerId", to_char(current_period_end, 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') AS period, updated_at::text AS version FROM paid_customers WHERE user_id = $1 ORDER BY id`;
function normalize(rows: any[]): BindingSnapshot[] {
  return rows.map((row) => ({ ...row, period: row.period }));
}

export function createRepairStore(pool: Pool): RepairStore {
  const read = async (userId: string, client: Pool | PoolClient = pool) =>
    normalize((await client.query(selectBindings, [userId])).rows);
  const store: RepairStore = {
    read,
    async compareAndSet(repair) {
      const client = await pool.connect();
      try {
        await client.query("BEGIN ISOLATION LEVEL SERIALIZABLE");
        // Lock existing rows and compare the complete binding set, including timestamps.
        await client.query(
          "SELECT id FROM paid_customers WHERE user_id = $1 FOR UPDATE",
          [repair.userId],
        );
        if (
          fingerprint(await read(repair.userId, client)) !==
          fingerprint(repair.before)
        )
          throw new Error("Concurrent billing update; preview again");
        for (const change of repair.changes)
          await client.query(
            "UPDATE paid_customers SET current_period_end = $1, period_verification_version = NULL, updated_at = clock_timestamp() WHERE id = $2 AND user_id = $3",
            [change.period, change.id, repair.userId],
          );
        const after = await read(repair.userId, client);
        await client.query("COMMIT");
        return after;
      } catch (error) {
        await client.query("ROLLBACK");
        throw error;
      } finally {
        client.release();
      }
    },
  };
  return store;
}
