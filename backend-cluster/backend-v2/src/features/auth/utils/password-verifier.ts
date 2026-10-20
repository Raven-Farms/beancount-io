import bcrypt from "bcryptjs";
import { ServiceUnavailableError } from "@/shared/errors";

// Matches the cost used by UserModel.updatePassword. This is comparison work
// for absent credentials only, never an account's credential or a login path.
const DUMMY_PASSWORD_HASH =
  "$2b$10$5mBgP06bwKPcyhp0Fg7sqeIACeCt.enWK4cu2U7FJjlUzB9as/vQS";
const MAX_PASSWORD_VERIFICATIONS = 8;
let activeVerifications = 0;

/** Bound real and dummy bcrypt work together; overload never builds a queue. */
export async function verifyPasswordWithCapacity(
  password: string,
  verify?: () => Promise<boolean>,
): Promise<boolean> {
  if (activeVerifications >= MAX_PASSWORD_VERIFICATIONS) {
    throw new ServiceUnavailableError("Password verification", 1);
  }
  activeVerifications += 1;
  try {
    if (verify) return await verify();
    await bcrypt.compare(password, DUMMY_PASSWORD_HASH);
    return false;
  } finally {
    activeVerifications -= 1;
  }
}
