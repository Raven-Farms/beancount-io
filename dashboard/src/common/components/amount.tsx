import type { ReactNode } from "react";
import { cn } from "@/common/lib/utils/utils";

/** Keep the sign, number, and unit in their source order inside RTL layouts. */
export function Amount({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <bdi dir="ltr" className={cn("[unicode-bidi:isolate]", className)}>
      {children}
    </bdi>
  );
}
