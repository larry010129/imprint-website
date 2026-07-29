import React, { createContext, useContext, useEffect, useState } from "react";

import { cn } from "@/lib/utils";

type SwitchContextValue = {
  value: string | null;
  setValue: (next: string) => void;
};

const SwitchContext = createContext<SwitchContextValue | null>(null);

export type SwitchProps = {
  children: React.ReactNode;
  name?: string;
  size?: "small" | "medium" | "large";
  style?: React.CSSProperties;
  className?: string;
  value?: string | null;
  onValueChange?: (value: string) => void;
};

export function Switch({
  children,
  name = "default",
  size = "medium",
  style,
  className,
  value: controlledValue,
  onValueChange,
}: SwitchProps) {
  const [uncontrolled, setUncontrolled] = useState<string | null>(null);
  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : uncontrolled;

  const setValue = (next: string) => {
    if (!isControlled) setUncontrolled(next);
    onValueChange?.(next);
  };

  return (
    <SwitchContext.Provider value={{ value, setValue }}>
      <div
        role="radiogroup"
        className={cn(
          "flex border border-stone-300 bg-stone-100 p-1",
          size === "small" && "h-8 rounded-md",
          size === "medium" && "h-10 rounded-md",
          size === "large" && "h-12 rounded-lg",
          className
        )}
        style={style}
      >
        {React.Children.map(children, (child) => {
          if (!React.isValidElement<SwitchControlProps>(child)) return child;
          return React.cloneElement(child, { size, name });
        })}
      </div>
    </SwitchContext.Provider>
  );
}

export type SwitchControlProps = {
  label?: string;
  value: string;
  defaultChecked?: boolean;
  disabled?: boolean;
  name?: string;
  size?: "small" | "medium" | "large";
  icon?: React.ReactNode;
};

function SwitchControl({
  label,
  value,
  defaultChecked,
  disabled = false,
  name,
  size = "medium",
  icon,
}: SwitchControlProps) {
  const context = useContext(SwitchContext);
  const checked = value === context?.value;

  useEffect(() => {
    if (defaultChecked && context && context.value == null) {
      context.setValue(value);
    }
    // Intentionally once on mount for uncontrolled default.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <label
      className={cn("flex h-full flex-1", disabled && "pointer-events-none cursor-not-allowed")}
      onClick={() => {
        if (!disabled) context?.setValue(value);
      }}
    >
      <input
        type="radio"
        name={name}
        value={value}
        disabled={disabled}
        checked={checked}
        onChange={() => context?.setValue(value)}
        className="hidden"
      />
      <span
        className={cn(
          "flex flex-1 cursor-pointer items-center justify-center font-sans font-medium duration-150",
          checked
            ? "rounded-sm bg-white text-stone-900 shadow-sm"
            : "text-stone-600 hover:text-stone-900",
          disabled && "text-stone-400",
          !icon && size === "small" && "px-3 text-sm",
          !icon && size === "medium" && "px-3 text-sm",
          !icon && size === "large" && "px-4 text-base",
          icon && size === "small" && "px-2 py-1",
          icon && size === "medium" && "px-3 py-2",
          icon && size === "large" && "p-3"
        )}
      >
        {icon ? <span className={cn(size === "large" && "scale-125")}>{icon}</span> : label}
      </span>
    </label>
  );
}

Switch.Control = SwitchControl;
