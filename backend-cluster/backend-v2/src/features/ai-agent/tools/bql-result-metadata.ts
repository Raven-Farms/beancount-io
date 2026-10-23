/** Same-query count for MCP text rendering; never part of the public envelope. */
export const BQL_ROW_COUNT = Symbol("bqlRowCount");

/** Set when `runBqlQuery` cut its rendered text at the ceiling (w23/010). */
export const BQL_TRUNCATED = Symbol("bqlTruncated");
