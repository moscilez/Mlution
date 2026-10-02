import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-brand text-brand-foreground shadow-glow hover:bg-brand/90 active:bg-brand/80",
        secondary:
          "bg-white/10 text-zinc-100 hover:bg-white/15 border border-white/10",
        outline:
          "border border-white/15 bg-transparent text-zinc-100 hover:bg-white/5 hover:border-white/25",
        ghost: "text-zinc-300 hover:bg-white/5 hover:text-zinc-100",
        destructive:
          "bg-red-500/90 text-white hover:bg-red-500 border border-red-400/30",
        link: "text-brand underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-lg px-3 text-xs",
        lg: "h-12 rounded-xl px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type = "button", ...props }, ref) => (
    <button
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      type={type}
      {...props}
    />
  )
);
Button.displayName = "Button";

export { Button, buttonVariants };
