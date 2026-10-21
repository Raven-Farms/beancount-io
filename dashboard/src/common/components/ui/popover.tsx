import * as React from "react";
import * as PopoverPrimitive from "@radix-ui/react-popover";

import { cn } from "@/common/lib/utils/utils.ts";

function Popover({
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Root>) {
  return <PopoverPrimitive.Root data-slot="popover" {...props} />;
}

function PopoverTrigger({
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Trigger>) {
  return <PopoverPrimitive.Trigger data-slot="popover-trigger" {...props} />;
}

/**
 * A popup is portaled to the body, outside any open Dialog or Sheet, whose
 * scroll lock cancels wheel and touch scrolling it did not start inside its
 * own content — so a date or account list inside a modal could not be
 * scrolled (w4/m40). The lock listens on `document`; stopping these two
 * events at the popup keeps its own scrolling while the page behind stays
 * locked. Clicks, keys and focus are untouched.
 */
function containPopupScroll(node: HTMLElement) {
  const stop = (event: Event) => event.stopPropagation();
  node.addEventListener("wheel", stop, { passive: true });
  node.addEventListener("touchmove", stop, { passive: true });
  return () => {
    node.removeEventListener("wheel", stop);
    node.removeEventListener("touchmove", stop);
  };
}

function PopoverContent({
  className,
  align = "center",
  sideOffset = 4,
  ref,
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Content>) {
  const contentRef = React.useCallback(
    (node: HTMLDivElement | null) => {
      if (typeof ref === "function") ref(node);
      else if (ref) ref.current = node;
      if (!node) return;
      const release = containPopupScroll(node);
      return () => {
        release();
        if (typeof ref === "function") ref(null);
        else if (ref) ref.current = null;
      };
    },
    [ref],
  );
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        ref={contentRef}
        data-slot="popover-content"
        align={align}
        sideOffset={sideOffset}
        className={cn(
          "bg-popover text-popover-foreground data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 z-50 w-72 origin-(--radix-popover-content-transform-origin) rounded-md border p-4 shadow-md outline-hidden",
          className,
        )}
        {...props}
      />
    </PopoverPrimitive.Portal>
  );
}

function PopoverAnchor({
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Anchor>) {
  return <PopoverPrimitive.Anchor data-slot="popover-anchor" {...props} />;
}

export { Popover, PopoverTrigger, PopoverContent, PopoverAnchor };
