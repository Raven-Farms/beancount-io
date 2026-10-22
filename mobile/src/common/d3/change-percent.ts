/**
 * Percent change from `baseline` to `value`, or null when no percentage means
 * anything: a zero start, or a start and end on opposite sides of zero (net
 * worth from −76 to +1,347 has no percent change). Measured against the
 * baseline's magnitude, so a liability shrinking from −1,000 to −500 reads
 * +50% rather than as a loss.
 */
export function changePercent(baseline: number, value: number): number | null {
  if (
    baseline === 0 ||
    (value !== 0 && Math.sign(value) !== Math.sign(baseline))
  ) {
    return null;
  }
  return ((value - baseline) / Math.abs(baseline)) * 100;
}

/**
 * The change row's percentage as it is shown: rounded to two places first, a
 * rounded -0 normalised to 0, and the sign and the verdict taken from the
 * rounded value, as the amount's sign is (w21/055). Prefixed from the raw
 * change, a move of -$12 on 2,500,000 read "-$12.00 (-0.00%)" in the
 * unfavourable colour, and a sub-cent gain "+$0.00 (-0.00%)" (w21/237).
 * `flat` is true when it rounds to nothing, which reads in the neutral colour.
 */
export function formatChangePercent(pct: number): {
  text: string;
  flat: boolean;
} {
  const rounded = Math.round(pct * 100) / 100 + 0;
  return {
    text: `${rounded > 0 ? "+" : ""}${rounded.toFixed(2)}%`,
    flat: rounded === 0,
  };
}
