import { memo, useMemo, type CSSProperties, type ElementType } from "react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";

interface ShimmerProps {
  children: string;
  as?: ElementType;
  className?: string;
  duration?: number;
  spread?: number;
}

const ShimmerComponent = ({
  children,
  as: Component = "p",
  className,
  duration = 2,
  spread = 2,
}: ShimmerProps) => {
  const MotionComponent = motion(Component as keyof React.JSX.IntrinsicElements);

  const dynamicSpread = useMemo(
    () => (children.length ?? 0) * spread,
    [children, spread],
  );

  return (
    <MotionComponent
      animate={{ backgroundPosition: "0% center" }}
      className={cn(
        "relative inline-block bg-[length:250%_100%,auto] bg-clip-text text-transparent",
        "[--shimmer-bg:linear-gradient(90deg,#0000_calc(50%-var(--shimmer-spread)),hsl(var(--background)),#0000_calc(50%+var(--shimmer-spread)))] [background-repeat:no-repeat,padding-box]",
        className,
      )}
      initial={{ backgroundPosition: "100% center" }}
      style={
        {
          "--shimmer-spread": `${dynamicSpread}px`,
          backgroundImage:
            "var(--shimmer-bg), linear-gradient(hsl(var(--muted-foreground)), hsl(var(--muted-foreground)))",
        } as CSSProperties
      }
      transition={{
        repeat: Infinity,
        duration,
        ease: "linear",
      }}
    >
      {children}
    </MotionComponent>
  );
};

export const Shimmer = memo(ShimmerComponent);
