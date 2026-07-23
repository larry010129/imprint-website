"use client";

import { AnimatePresence, motion } from "motion/react";
import type React from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { createPortal } from "react-dom";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const PADDING = 16;
const CONTENT_WIDTH = 300;
const CONTENT_MIN_HEIGHT = 140;
const VIEWPORT_MARGIN = 12;
/** Space reserved at bottom for fixed-bottom tooltip (px) */
function getTooltipBottomReserve() {
  if (typeof window === "undefined") return 200;
  const tourMobile =
    window.matchMedia("(max-width: 900px)").matches ||
    window.matchMedia("(orientation: portrait) and (max-width: 1280px)").matches;
  return tourMobile ? 210 : 200;
}

export interface TourStep {
  content: React.ReactNode;
  selectorId: string;
  width?: number;
  height?: number;
  /** Shrink spotlight inside the target element (px) */
  padding?: number | { top?: number; right?: number; bottom?: number; left?: number };
  /** Expand spotlight outside the measured bounds (px) */
  outset?: number | { top?: number; right?: number; bottom?: number; left?: number };
  maxWidth?: number;
  maxHeight?: number;
  /** Measure visible children instead of the container box (for flex grids) */
  boundsMode?: "element" | "content";
  contentSelector?: string;
  /** When false, do not shrink spotlight to stay above fixed-bottom tooltip */
  clampToViewport?: boolean;
  /** Override provider tooltip placement for this step */
  tooltipMode?: "auto" | "fixed-bottom";
  onClickWithinArea?: () => void;
  position?: "top" | "bottom" | "left" | "right";
}

interface TourContextType {
  currentStep: number;
  totalSteps: number;
  nextStep: () => void;
  previousStep: () => void;
  endTour: () => void;
  isActive: boolean;
  startTour: () => void;
  setSteps: (steps: TourStep[]) => void;
  steps: TourStep[];
  isTourCompleted: boolean;
  setIsTourCompleted: (completed: boolean) => void;
}

interface TourProviderProps {
  children: React.ReactNode;
  onComplete?: () => void;
  className?: string;
  isTourCompleted?: boolean;
  /** Pin tooltip to bottom center — keeps controls visible without page scroll */
  tooltipMode?: "auto" | "fixed-bottom";
}

const TourContext = createContext<TourContextType | null>(null);

function getFixedBottomTooltipPosition() {
  const width = Math.min(CONTENT_WIDTH, window.innerWidth - VIEWPORT_MARGIN * 2);
  return {
    top: window.innerHeight - VIEWPORT_MARGIN,
    left: (window.innerWidth - width) / 2,
    width,
    transform: "translateY(-100%)",
  };
}

function getElementPosition(id: string) {
  const element = document.getElementById(id);
  if (!element) return null;
  const rect = element.getBoundingClientRect();
  return {
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height,
  };
}

function getContentUnionRect(containerId: string, childSelector: string) {
  const container = document.getElementById(containerId);
  if (!container) return null;

  const children = Array.from(container.querySelectorAll(childSelector));

  if (children.length === 0) return getElementPosition(containerId);

  let top = Number.POSITIVE_INFINITY;
  let left = Number.POSITIVE_INFINITY;
  let right = Number.NEGATIVE_INFINITY;
  let bottom = Number.NEGATIVE_INFINITY;

  for (const child of children) {
    const el = child as HTMLElement;
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) continue;
    top = Math.min(top, rect.top);
    left = Math.min(left, rect.left);
    right = Math.max(right, rect.right);
    bottom = Math.max(bottom, rect.bottom);
  }

  if (!Number.isFinite(top)) return getElementPosition(containerId);

  return {
    top,
    left,
    width: right - left,
    height: bottom - top,
  };
}

function getSpotlightRaw(step: TourStep) {
  if (step.boundsMode === "content" && step.contentSelector) {
    return getContentUnionRect(step.selectorId, step.contentSelector);
  }
  return getElementPosition(step.selectorId);
}

function resolvePadding(padding?: TourStep["padding"]) {
  if (padding == null) return { top: 0, right: 0, bottom: 0, left: 0 };
  if (typeof padding === "number") {
    return { top: padding, right: padding, bottom: padding, left: padding };
  }
  const base = padding.top ?? padding.left ?? padding.right ?? padding.bottom ?? 0;
  return {
    top: padding.top ?? base,
    right: padding.right ?? base,
    bottom: padding.bottom ?? base,
    left: padding.left ?? base,
  };
}

function resolveOutset(outset?: TourStep["outset"]) {
  if (outset == null) return { top: 0, right: 0, bottom: 0, left: 0 };
  if (typeof outset === "number") {
    return { top: outset, right: outset, bottom: outset, left: outset };
  }
  const base = outset.top ?? outset.left ?? outset.right ?? outset.bottom ?? 0;
  return {
    top: outset.top ?? base,
    right: outset.right ?? base,
    bottom: outset.bottom ?? base,
    left: outset.left ?? base,
  };
}

function resolveSpotlightRect(
  step: TourStep,
  raw: { top: number; left: number; width: number; height: number },
  tooltipMode: TourProviderProps["tooltipMode"],
) {
  const out = resolveOutset(step.outset);
  let top = raw.top - out.top;
  let left = raw.left - out.left;
  let width = raw.width + out.left + out.right;
  let height = raw.height + out.top + out.bottom;

  const pad = resolvePadding(step.padding);
  top += pad.top;
  left += pad.left;
  width -= pad.left + pad.right;
  height -= pad.top + pad.bottom;

  if (step.width != null) width = step.width;
  if (step.height != null) height = step.height;
  if (step.maxWidth != null) width = Math.min(width, step.maxWidth);
  if (step.maxHeight != null) height = Math.min(height, step.maxHeight);

  const stepTooltipMode = step.tooltipMode ?? tooltipMode;
  const shouldClamp = step.clampToViewport !== false && stepTooltipMode === "fixed-bottom";
  if (shouldClamp) {
    const maxBottom = window.innerHeight - getTooltipBottomReserve();
    if (top + height > maxBottom) height = maxBottom - top;
  }

  width = Math.max(48, width);
  height = Math.max(48, height);

  return { top, left, width, height };
}

function calculateContentPosition(
  elementPos: { top: number; left: number; width: number; height: number },
  position: "top" | "bottom" | "left" | "right" = "bottom",
) {
  let left = elementPos.left;
  let top = elementPos.top;

  switch (position) {
    case "top":
      top = elementPos.top - CONTENT_MIN_HEIGHT - PADDING;
      left = elementPos.left + elementPos.width / 2 - CONTENT_WIDTH / 2;
      break;
    case "bottom":
      top = elementPos.top + elementPos.height + PADDING;
      left = elementPos.left + elementPos.width / 2 - CONTENT_WIDTH / 2;
      break;
    case "left":
      left = elementPos.left - CONTENT_WIDTH - PADDING;
      top = elementPos.top + elementPos.height / 2 - CONTENT_MIN_HEIGHT / 2;
      break;
    case "right":
      left = elementPos.left + elementPos.width + PADDING;
      top = elementPos.top + elementPos.height / 2 - CONTENT_MIN_HEIGHT / 2;
      break;
  }

  const maxLeft = window.innerWidth - CONTENT_WIDTH - VIEWPORT_MARGIN;
  const maxTop = window.innerHeight - CONTENT_MIN_HEIGHT - VIEWPORT_MARGIN;

  return {
    top: Math.max(VIEWPORT_MARGIN, Math.min(top, maxTop)),
    left: Math.max(VIEWPORT_MARGIN, Math.min(left, maxLeft)),
    width: CONTENT_WIDTH,
  };
}

export function TourProvider({
  children,
  onComplete,
  className,
  isTourCompleted = false,
  tooltipMode = "auto",
}: TourProviderProps) {
  const [steps, setSteps] = useState<TourStep[]>([]);
  const [currentStep, setCurrentStep] = useState(-1);
  const [elementPosition, setElementPosition] = useState<{
    top: number;
    left: number;
    width: number;
    height: number;
  } | null>(null);
  const [isCompleted, setIsCompleted] = useState(isTourCompleted);

  const updateElementPosition = useCallback(() => {
    if (currentStep >= 0 && currentStep < steps.length) {
      const step = steps[currentStep];
      const raw = getSpotlightRaw(step);
      if (!raw) return;
      setElementPosition(resolveSpotlightRect(step, raw, tooltipMode));
    }
  }, [currentStep, steps, tooltipMode]);

  useEffect(() => {
    if (currentStep < 0) return;
    if (currentStep !== 3) window.scrollTo(0, 0);
    updateElementPosition();
    const raf1 = window.requestAnimationFrame(() => {
      updateElementPosition();
      window.requestAnimationFrame(updateElementPosition);
    });
    const t1 = window.setTimeout(updateElementPosition, 120);
    const t2 = window.setTimeout(updateElementPosition, 320);
    window.addEventListener("resize", updateElementPosition);
    window.addEventListener("scroll", updateElementPosition, true);
    return () => {
      window.cancelAnimationFrame(raf1);
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.removeEventListener("resize", updateElementPosition);
      window.removeEventListener("scroll", updateElementPosition, true);
    };
  }, [currentStep, updateElementPosition]);

  const nextStep = useCallback(() => {
    setCurrentStep((prev) => {
      if (prev >= steps.length - 1) {
        setIsCompleted(true);
        onComplete?.();
        return -1;
      }
      return prev + 1;
    });
  }, [steps.length, onComplete]);

  const previousStep = useCallback(() => {
    setCurrentStep((prev) => (prev > 0 ? prev - 1 : prev));
  }, []);

  const endTour = useCallback(() => {
    setCurrentStep(-1);
  }, []);

  const startTour = useCallback(() => {
    if (isCompleted) return;
    setCurrentStep(0);
  }, [isCompleted]);

  const handleClick = useCallback(
    (e: MouseEvent) => {
      if (currentStep >= 0 && elementPosition && steps[currentStep]?.onClickWithinArea) {
        const w = elementPosition.width;
        const h = elementPosition.height;
        const isWithinBounds =
          e.clientX >= elementPosition.left &&
          e.clientX <= elementPosition.left + w &&
          e.clientY >= elementPosition.top &&
          e.clientY <= elementPosition.top + h;
        if (isWithinBounds) steps[currentStep].onClickWithinArea?.();
      }
    },
    [currentStep, elementPosition, steps],
  );

  useEffect(() => {
    window.addEventListener("click", handleClick);
    return () => window.removeEventListener("click", handleClick);
  }, [handleClick]);

  const setIsTourCompleted = useCallback((completed: boolean) => {
    setIsCompleted(completed);
  }, []);

  return (
    <TourContext.Provider
      value={{
        currentStep,
        totalSteps: steps.length,
        nextStep,
        previousStep,
        endTour,
        isActive: currentStep >= 0,
        startTour,
        setSteps,
        steps,
        isTourCompleted: isCompleted,
        setIsTourCompleted,
      }}
    >
      {children}
      {typeof document !== "undefined" &&
        createPortal(
          <div data-shop-tour-root className="shop-tour-portal">
          <AnimatePresence>
            {currentStep >= 0 && elementPosition && steps[currentStep] && (() => {
              const step = steps[currentStep];
              const spotW = elementPosition.width;
              const spotH = elementPosition.height;
              const stepTooltipMode = step.tooltipMode ?? tooltipMode;
              const tooltipPos =
                stepTooltipMode === "fixed-bottom"
                  ? getFixedBottomTooltipPosition()
                  : calculateContentPosition(elementPosition, step?.position ?? "bottom");
              const tooltipWidth = stepTooltipMode === "fixed-bottom" ? tooltipPos.width : CONTENT_WIDTH;
              return (
              <>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="pointer-events-none fixed inset-0 z-[700] overflow-hidden bg-black/50"
                  style={{
                    clipPath: `polygon(
                  0% 0%, 0% 100%, 100% 100%, 100% 0%,
                  ${elementPosition.left}px 0%,
                  ${elementPosition.left}px ${elementPosition.top}px,
                  ${elementPosition.left + spotW}px ${elementPosition.top}px,
                  ${elementPosition.left + spotW}px ${elementPosition.top + spotH}px,
                  ${elementPosition.left}px ${elementPosition.top + spotH}px,
                  ${elementPosition.left}px 0%
                )`,
                  }}
                />
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  style={{
                    position: "fixed",
                    top: elementPosition.top,
                    left: elementPosition.left,
                    width: spotW,
                    height: spotH,
                  }}
                  className={cn("pointer-events-none z-[701] rounded-xl border-2 border-primary shadow-[0_0_0_1px_rgba(94,207,207,0.35)]", className)}
                />
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{
                    opacity: 1,
                    y: 0,
                    top: tooltipPos.top,
                    left: tooltipPos.left,
                    ...(stepTooltipMode === "fixed-bottom" ? { transform: "translateY(-100%)" } : {}),
                  }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                  exit={{ opacity: 0, y: 10 }}
                  style={{ position: "fixed", zIndex: 702, width: tooltipWidth }}
                  className="pointer-events-auto relative flex max-h-[min(28vh,200px)] flex-col rounded-lg border bg-background p-4 pb-4 shadow-lg"
                >
                  <div className="absolute right-4 top-2 text-xs text-muted-foreground">
                    {currentStep + 1} / {steps.length}
                  </div>
                  <div className="flex flex-1 flex-col pt-5">
                    <motion.div
                      key={`tour-content-${currentStep}`}
                      initial={{ opacity: 0, scale: 0.95, filter: "blur(4px)" }}
                      animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                      exit={{ opacity: 0, scale: 0.95, filter: "blur(4px)" }}
                      transition={{ duration: 0.2 }}
                    >
                      {steps[currentStep]?.content}
                    </motion.div>
                    <div className="mt-4 flex items-center justify-between gap-2 border-t border-border pt-3">
                      {currentStep > 0 ? (
                        <Button type="button" onClick={previousStep} variant="ghost" className="text-sm">
                          上一步
                        </Button>
                      ) : (
                        <span aria-hidden="true" />
                      )}
                      <Button type="button" onClick={nextStep} variant="default" className="text-sm">
                        {currentStep === steps.length - 1 ? "完成" : "下一步"}
                      </Button>
                    </div>
                  </div>
                </motion.div>
              </>
              );
            })()}
          </AnimatePresence>
          </div>,
          document.body,
        )}
    </TourContext.Provider>
  );
}

export function useTour() {
  const context = useContext(TourContext);
  if (!context) throw new Error("useTour must be used within a TourProvider");
  return context;
}

export function TourWelcomeDialog({
  isOpen,
  setIsOpen,
  title,
  description,
  startLabel = "開始導覽",
  skipLabel = "略過",
  onSkip,
  onStart,
}: {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
  title: React.ReactNode;
  description: React.ReactNode;
  startLabel?: string;
  skipLabel?: string;
  onSkip?: () => void;
  onStart?: () => void;
}) {
  const { steps, isTourCompleted, currentStep, setIsTourCompleted } = useTour();

  if (isTourCompleted || steps.length === 0 || currentStep > -1 || !isOpen) {
    return null;
  }

  const handleSkip = () => {
    onSkip?.();
    setIsTourCompleted(true);
    setIsOpen(false);
  };

  const handleStart = () => {
    setIsOpen(false);
    if (onStart) onStart();
  };

  return (
    <div className="fixed inset-0 z-[600] flex items-center justify-center bg-black/40 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="w-full max-w-md rounded-xl border bg-background p-6 shadow-xl"
      >
        <div className="flex flex-col items-center text-center">
          <div className="mb-4 text-primary">{title}</div>
          <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
        </div>
        <div className="mt-6 space-y-3">
          <Button onClick={handleStart} className="w-full">
            {startLabel}
          </Button>
          <Button onClick={handleSkip} variant="ghost" className="w-full">
            {skipLabel}
          </Button>
        </div>
      </motion.div>
    </div>
  );
}
