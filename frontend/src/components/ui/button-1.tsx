import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-primary-foreground shadow-xs hover:bg-primary/90",
        destructive:
          "bg-destructive text-white shadow-xs hover:bg-destructive/90 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40 dark:bg-destructive/60",
        outline:
          "border border-input bg-background shadow-xs hover:bg-accent hover:text-accent-foreground dark:bg-input/30 dark:hover:bg-input/50",
        secondary:
          "bg-secondary text-secondary-foreground shadow-xs hover:bg-secondary/80",
        ghost:
          "hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/50",
        dim: "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground",
      },
      mode: {
        default: "",
        icon: "[&_svg:not([class*='size-'])]:size-4",
        link: "h-auto p-0 text-primary underline-offset-4 hover:underline",
      },
      size: {
        sm: "h-7 gap-1 rounded-md px-2.5 text-xs has-[>svg]:px-2",
        md: "h-9 px-4 py-2 has-[>svg]:px-3",
        lg: "h-10 rounded-md px-6 text-base has-[>svg]:px-4",
        icon: "size-9 [&_svg:not([class*='size-'])]:size-4",
      },
    },
    compoundVariants: [
      {
        mode: "link",
        className: "shadow-none",
      },
      {
        mode: "icon",
        size: "sm",
        className: "size-7",
      },
      {
        mode: "icon",
        size: "md",
        className: "size-9",
      },
      {
        mode: "icon",
        size: "lg",
        className: "size-10",
      },
    ],
    defaultVariants: {
      variant: "primary",
      mode: "default",
      size: "md",
    },
  },
)

type Button1Props = React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }

function Button({
  className,
  variant,
  mode,
  size,
  asChild = false,
  ...props
}: Button1Props) {
  const Comp = asChild ? Slot : "button"
  const resolvedSize = mode === "icon" && !size ? "icon" : size

  return (
    <Comp
      data-slot="button-1"
      className={cn(
        buttonVariants({ variant, mode, size: resolvedSize }),
        className,
      )}
      {...props}
    />
  )
}

export { Button, Button as Button1, buttonVariants }
