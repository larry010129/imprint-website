import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden whitespace-nowrap rounded-md border font-medium transition-[color,box-shadow] focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 [&>svg]:pointer-events-none",
  {
    variants: {
      variant: {
        primary: "",
        secondary: "",
        destructive: "",
        outline: "",
        success: "",
        warning: "",
        info: "",
      },
      appearance: {
        default: "",
        light: "",
        outline: "bg-transparent",
        ghost: "border-transparent bg-transparent",
      },
      size: {
        xs: "px-1.5 py-0 text-[10px] [&>svg]:size-2.5",
        sm: "px-2 py-0.5 text-xs [&>svg]:size-3",
        md: "px-2.5 py-0.5 text-xs [&>svg]:size-3",
        lg: "px-3 py-1 text-sm [&>svg]:size-3.5",
      },
    },
    compoundVariants: [
      {
        variant: "primary",
        appearance: "default",
        className:
          "border-transparent bg-primary text-primary-foreground [a&]:hover:bg-primary/90",
      },
      {
        variant: "primary",
        appearance: "light",
        className:
          "border-transparent bg-primary/15 text-primary [a&]:hover:bg-primary/25",
      },
      {
        variant: "primary",
        appearance: "outline",
        className:
          "border-primary/40 text-primary [a&]:hover:bg-primary/10",
      },
      {
        variant: "primary",
        appearance: "ghost",
        className: "text-primary [a&]:hover:bg-primary/10",
      },
      {
        variant: "secondary",
        appearance: "default",
        className:
          "border-transparent bg-secondary text-secondary-foreground [a&]:hover:bg-secondary/90",
      },
      {
        variant: "secondary",
        appearance: "light",
        className:
          "border-transparent bg-secondary/60 text-secondary-foreground [a&]:hover:bg-secondary/80",
      },
      {
        variant: "secondary",
        appearance: "outline",
        className:
          "border-border text-secondary-foreground [a&]:hover:bg-secondary/50",
      },
      {
        variant: "secondary",
        appearance: "ghost",
        className:
          "text-secondary-foreground [a&]:hover:bg-secondary/50",
      },
      {
        variant: "destructive",
        appearance: "default",
        className:
          "border-transparent bg-destructive text-white [a&]:hover:bg-destructive/90 focus-visible:ring-destructive/20",
      },
      {
        variant: "destructive",
        appearance: "light",
        className:
          "border-transparent bg-destructive/15 text-destructive [a&]:hover:bg-destructive/25",
      },
      {
        variant: "destructive",
        appearance: "outline",
        className:
          "border-destructive/40 text-destructive [a&]:hover:bg-destructive/10",
      },
      {
        variant: "destructive",
        appearance: "ghost",
        className: "text-destructive [a&]:hover:bg-destructive/10",
      },
      {
        variant: "outline",
        appearance: "default",
        className:
          "text-foreground [a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
      },
      {
        variant: "outline",
        appearance: "light",
        className:
          "border-border/60 bg-muted/50 text-foreground [a&]:hover:bg-muted",
      },
      {
        variant: "outline",
        appearance: "outline",
        className:
          "border-input text-foreground [a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
      },
      {
        variant: "outline",
        appearance: "ghost",
        className:
          "text-foreground [a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
      },
      {
        variant: "success",
        appearance: "default",
        className:
          "border-transparent bg-emerald-600 text-white [a&]:hover:bg-emerald-600/90",
      },
      {
        variant: "success",
        appearance: "light",
        className:
          "border-transparent bg-emerald-500/15 text-emerald-700 [a&]:hover:bg-emerald-500/25 dark:text-emerald-400",
      },
      {
        variant: "success",
        appearance: "outline",
        className:
          "border-emerald-500/40 text-emerald-700 [a&]:hover:bg-emerald-500/10 dark:text-emerald-400",
      },
      {
        variant: "success",
        appearance: "ghost",
        className:
          "text-emerald-700 [a&]:hover:bg-emerald-500/10 dark:text-emerald-400",
      },
      {
        variant: "warning",
        appearance: "default",
        className:
          "border-transparent bg-amber-500 text-white [a&]:hover:bg-amber-500/90",
      },
      {
        variant: "warning",
        appearance: "light",
        className:
          "border-transparent bg-amber-500/15 text-amber-700 [a&]:hover:bg-amber-500/25 dark:text-amber-400",
      },
      {
        variant: "warning",
        appearance: "outline",
        className:
          "border-amber-500/40 text-amber-700 [a&]:hover:bg-amber-500/10 dark:text-amber-400",
      },
      {
        variant: "warning",
        appearance: "ghost",
        className:
          "text-amber-700 [a&]:hover:bg-amber-500/10 dark:text-amber-400",
      },
      {
        variant: "info",
        appearance: "default",
        className:
          "border-transparent bg-sky-600 text-white [a&]:hover:bg-sky-600/90",
      },
      {
        variant: "info",
        appearance: "light",
        className:
          "border-transparent bg-sky-500/15 text-sky-700 [a&]:hover:bg-sky-500/25 dark:text-sky-400",
      },
      {
        variant: "info",
        appearance: "outline",
        className:
          "border-sky-500/40 text-sky-700 [a&]:hover:bg-sky-500/10 dark:text-sky-400",
      },
      {
        variant: "info",
        appearance: "ghost",
        className:
          "text-sky-700 [a&]:hover:bg-sky-500/10 dark:text-sky-400",
      },
    ],
    defaultVariants: {
      variant: "primary",
      appearance: "default",
      size: "md",
    },
  },
)

function Badge({
  className,
  variant,
  appearance,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "span"

  return (
    <Comp
      data-slot="badge-2"
      className={cn(badgeVariants({ variant, appearance, size }), className)}
      {...props}
    />
  )
}

export { Badge, Badge as Badge2, badgeVariants }
