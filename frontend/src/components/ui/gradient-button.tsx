"use client"

import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const gradientButtonVariants = cva(
  [
    "gradient-button",
    "relative isolate inline-flex p-[2px]",
    "overflow-hidden",
    "focus-within:outline-none focus-within:ring-1 focus-within:ring-[#5ECFCF]",
    "disabled:pointer-events-none disabled:opacity-50",
  ],
  {
    variants: {
      variant: {
        default: "",
        animated: "gradient-button-variant",
      },
      size: {
        default: "rounded-[11px] [&_.gradient-button-inner]:min-w-[132px] [&_.gradient-button-inner]:rounded-[9px] [&_.gradient-button-inner]:px-9 [&_.gradient-button-inner]:py-4 [&_.gradient-button-inner]:text-base [&_.gradient-button-inner]:leading-[19px]",
        nav: "rounded-[9px] [&_.gradient-button-inner]:min-w-0 [&_.gradient-button-inner]:rounded-[7px] [&_.gradient-button-inner]:px-4 [&_.gradient-button-inner]:py-2.5 [&_.gradient-button-inner]:text-[12.5px] [&_.gradient-button-inner]:leading-none [&_.gradient-button-inner]:whitespace-nowrap",
      },
    },
    defaultVariants: {
      variant: "animated",
      size: "default",
    },
  },
)

const innerClass = "gradient-button-inner font-sans font-medium"

export interface GradientButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof gradientButtonVariants> {
  asChild?: boolean
  href?: string
}

const GradientButton = React.forwardRef<HTMLButtonElement, GradientButtonProps>(
  ({ className, variant, size, asChild = false, href, children, ...props }, ref) => {
    const outerClass = cn(gradientButtonVariants({ variant, size, className }))

    if (href) {
      return (
        <div className={outerClass}>
          <a href={href} className={innerClass}>
            {children}
          </a>
        </div>
      )
    }

    if (asChild && React.isValidElement(children)) {
      return (
        <div className={outerClass}>
          <Slot ref={ref} className={innerClass} {...props}>
            {children}
          </Slot>
        </div>
      )
    }

    return (
      <div className={outerClass}>
        <button type="button" className={innerClass} ref={ref} {...props}>
          {children}
        </button>
      </div>
    )
  },
)
GradientButton.displayName = "GradientButton"

export { GradientButton, gradientButtonVariants }
