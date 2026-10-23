import { cn } from "@/common/lib/utils/utils";

/**
 * Pressed styling for a filter button.
 *
 * Forced colors drops the shadow and maps both states' text and border onto
 * the same system colours, so fill-plus-shadow stopped telling a pressed
 * filter from an unpressed neighbour — the reader could not see which filters
 * had emptied the result. System colour keywords are honoured in that mode, so
 * a pressed button claims Highlight, with a readable label (w4/m43), while the
 * rest sink into Canvas. The two
 * branches are mutually exclusive rather than layered, since same-specificity
 * utilities would otherwise resolve in an order this file does not control.
 * Focus gets its own outline, because the shared Button's ring is a shadow.
 */
export function filterButtonState(active: boolean) {
  return cn(
    active
      ? "border-border shadow-xs forced-selected"
      : cn(
          "border-transparent text-muted-foreground",
          "forced-colors:border-[Canvas]",
        ),
    "forced-colors:focus-visible:[outline-style:solid] forced-colors:focus-visible:outline-2 forced-colors:focus-visible:outline-offset-2 forced-colors:focus-visible:outline-[CanvasText]",
  );
}
