/**
 * A short confetti burst for a payment that went through. Skipped when the
 * reader prefers reduced motion; the library loads only here, so it never
 * reaches the entry chunk.
 */
export async function celebrate(): Promise<void> {
  if (typeof window === "undefined") return;
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
  try {
    const { default: confetti } = await import("canvas-confetti");
    await confetti({
      particleCount: 120,
      spread: 75,
      origin: { y: 0.6 },
      disableForReducedMotion: true,
    });
  } catch {
    // A chunk that fails to load only costs the celebration.
  }
}
