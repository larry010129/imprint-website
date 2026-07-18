import { useEffect, useState } from "react";
import { Gem } from "lucide-react";
import { motion } from "motion/react";
import {
  TourProvider,
  TourWelcomeDialog,
  useTour,
  type TourStep,
} from "@/components/ui/tour";

const STORAGE_KEY = "imprint_shop_tour_v2";
/** Phone + laptop portrait (DevTools vertical / narrow tall window) */
const TOUR_MOBILE_MQ = "(max-width: 900px), (orientation: portrait) and (max-width: 1280px)";

function isTourMobileLayout() {
  return typeof window !== "undefined" && window.matchMedia(TOUR_MOBILE_MQ).matches;
}

declare global {
  interface Window {
    shopTour?: {
      isReady: () => boolean;
      goToStep: (stepIndex: number) => void;
      scrollToProductConfig: () => void;
      reset: () => void;
    };
  }
}

export const SHOP_TOUR_IDS = {
  STEPPER: "shop-wizard-header",
  CATALOG: "catalog-grid",
  CATALOG_SECTION: "shop-catalog",
  STYLES: "type-grid",
  STYLES_SECTION: "shop-styles",
  PRODUCT: "product-layout",
  PRODUCT_BUY: "product-buy-col",
  PRICE: "shop-price-panel",
  MOBILE_PRICE: "mobile-buy-bar",
} as const;

function useMobileShop() {
  const [isMobile, setIsMobile] = useState(() => isTourMobileLayout());

  useEffect(() => {
    const sync = () => setIsMobile(isTourMobileLayout());
    sync();
    const mqs = [
      window.matchMedia("(max-width: 900px)"),
      window.matchMedia("(orientation: portrait) and (max-width: 1280px)"),
    ];
    mqs.forEach((mq) => mq.addEventListener("change", sync));
    window.addEventListener("resize", sync);
    return () => {
      mqs.forEach((mq) => mq.removeEventListener("change", sync));
      window.removeEventListener("resize", sync);
    };
  }, []);

  return isMobile;
}

function buildTourSteps(isMobile: boolean): TourStep[] {
  return [
    {
      selectorId: SHOP_TOUR_IDS.STEPPER,
      padding: isMobile ? 4 : 6,
      position: "bottom",
      content: (
        <div className="space-y-2">
          <h3 className="font-medium">三步驟完成訂製</h3>
          <p className="text-sm text-muted-foreground">
            依序選品項、款式、配置下單。上方進度條會標示您目前所在步驟。
          </p>
        </div>
      ),
    },
    {
      selectorId: isMobile ? SHOP_TOUR_IDS.CATALOG_SECTION : SHOP_TOUR_IDS.CATALOG,
      boundsMode: "content",
      contentSelector: isMobile
        ? ".shop-section-title, .catalog-tile"
        : ".catalog-tile",
      outset: isMobile ? 6 : 6,
      clampToViewport: false,
      position: "bottom",
      content: (
        <div className="space-y-2">
          <h3 className="font-medium">選擇品項</h3>
          <p className="text-sm text-muted-foreground">
            點選戒指、項墜、耳飾、手鍊或鍊條，進入該類別的款式列表。
          </p>
        </div>
      ),
    },
    {
      selectorId: isMobile ? SHOP_TOUR_IDS.STYLES_SECTION : SHOP_TOUR_IDS.STYLES,
      boundsMode: "content",
      contentSelector: isMobile
        ? ".shop-back, .shop-section-title, .catalog-filters-wrap, .type-card"
        : ".type-card",
      outset: isMobile ? 6 : 6,
      clampToViewport: false,
      position: "bottom",
      content: (
        <div className="space-y-2">
          <h3 className="font-medium">挑選款式</h3>
          <p className="text-sm text-muted-foreground">
            瀏覽款式卡片，可用搜尋與篩選縮小範圍，點選卡片進入配置。
          </p>
        </div>
      ),
    },
    isMobile
      ? {
          selectorId: SHOP_TOUR_IDS.PRODUCT_BUY,
          boundsMode: "content",
          contentSelector:
            ".product-info-header, #product-options-section, #ringsize-step",
          outset: 6,
          clampToViewport: false,
          position: "bottom",
          content: (
            <div className="space-y-2">
              <h3 className="font-medium">配置規格</h3>
              <p className="text-sm text-muted-foreground">
                選擇克拉、金屬與戒圍等規格；可點愛心收藏目前配置。
              </p>
            </div>
          ),
        }
      : {
          selectorId: SHOP_TOUR_IDS.PRODUCT,
          outset: 6,
          clampToViewport: false,
          position: "bottom",
          content: (
            <div className="space-y-2">
              <h3 className="font-medium">配置規格</h3>
              <p className="text-sm text-muted-foreground">
                左側預覽、右側選克拉與金屬等規格；可點愛心收藏目前配置。
              </p>
            </div>
          ),
        },
    isMobile
      ? {
          selectorId: SHOP_TOUR_IDS.MOBILE_PRICE,
          outset: 2,
          clampToViewport: false,
          tooltipMode: "auto",
          position: "top",
          content: (
            <div className="space-y-2">
              <h3 className="font-medium">試算價格與下單</h3>
              <p className="text-sm text-muted-foreground">
                底部列顯示總價；點「明細」可展開試算，完成後可訂購或加入購物車。
              </p>
            </div>
          ),
        }
      : {
          selectorId: SHOP_TOUR_IDS.PRICE,
          clampToViewport: false,
          position: "bottom",
          content: (
            <div className="space-y-2">
              <h3 className="font-medium">試算價格與下單</h3>
              <p className="text-sm text-muted-foreground">
                右側面板即時顯示總價與明細；完成選項後可確認訂購或加入購物車。
              </p>
            </div>
          ),
        },
  ];
}

function readTourCompleted(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function markTourCompleted() {
  try {
    localStorage.setItem(STORAGE_KEY, "1");
  } catch {
    /* ignore */
  }
}

function ShopTourSteps({ isMobile }: { isMobile: boolean }) {
  const { setSteps } = useTour();

  useEffect(() => {
    setSteps(buildTourSteps(isMobile));
  }, [isMobile, setSteps]);

  return null;
}

function ShopTourScrollLock() {
  const { isActive } = useTour();

  useEffect(() => {
    document.documentElement.classList.toggle("shop-tour-active", isActive);
    if (isActive) window.scrollTo(0, 0);
    return () => document.documentElement.classList.remove("shop-tour-active");
  }, [isActive]);

  return null;
}

function ShopTourStepClass() {
  const { currentStep, isActive } = useTour();

  useEffect(() => {
    const root = document.documentElement;
    for (let i = 0; i < 5; i += 1) root.classList.remove(`shop-tour-step-${i}`);
    if (isActive && currentStep >= 0) root.classList.add(`shop-tour-step-${currentStep}`);
    return () => {
      for (let i = 0; i < 5; i += 1) root.classList.remove(`shop-tour-step-${i}`);
    };
  }, [currentStep, isActive]);

  return null;
}

function ShopTourSync() {
  const { currentStep, isActive } = useTour();

  useEffect(() => {
    if (!isActive || currentStep < 0) return;
    window.shopTour?.goToStep(currentStep);
    if (currentStep === 3) {
      const scroll = () => window.shopTour?.scrollToProductConfig();
      scroll();
      const s1 = window.setTimeout(scroll, 180);
      const s2 = window.setTimeout(scroll, 450);
      const s3 = window.setTimeout(scroll, 750);
      const t1 = window.setTimeout(() => window.dispatchEvent(new Event("resize")), 120);
      const t2 = window.setTimeout(() => window.dispatchEvent(new Event("resize")), 350);
      const t3 = window.setTimeout(() => window.dispatchEvent(new Event("resize")), 600);
      return () => {
        window.clearTimeout(s1);
        window.clearTimeout(s2);
        window.clearTimeout(s3);
        window.clearTimeout(t1);
        window.clearTimeout(t2);
        window.clearTimeout(t3);
      };
    }
    const t1 = window.setTimeout(() => window.dispatchEvent(new Event("resize")), 120);
    const t2 = window.setTimeout(() => window.dispatchEvent(new Event("resize")), 350);
    const t3 = window.setTimeout(() => window.dispatchEvent(new Event("resize")), 600);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      window.clearTimeout(t3);
    };
  }, [currentStep, isActive]);

  return null;
}

function ShopTourRunner({
  isMobile,
  showWelcome,
  setShowWelcome,
  tourPending,
  setTourPending,
}: {
  isMobile: boolean;
  showWelcome: boolean;
  setShowWelcome: (v: boolean) => void;
  tourPending: boolean;
  setTourPending: (v: boolean) => void;
}) {
  const { startTour, isActive, totalSteps } = useTour();

  useEffect(() => {
    if (!tourPending || isActive || totalSteps === 0) return;
    const id = window.setTimeout(() => {
      startTour();
      setTourPending(false);
    }, 150);
    return () => window.clearTimeout(id);
  }, [tourPending, isActive, totalSteps, startTour, setTourPending]);

  return (
    <>
      <ShopTourSteps isMobile={isMobile} />
      <ShopTourScrollLock />
      <ShopTourStepClass />
      <ShopTourSync />
      <TourWelcomeDialog
        isOpen={showWelcome}
        setIsOpen={setShowWelcome}
        onSkip={markTourCompleted}
        onStart={() => {
          setShowWelcome(false);
          setTourPending(true);
        }}
        title={
          <motion.div
            initial={{ scale: 0.85, filter: "blur(6px)" }}
            animate={{ scale: 1, filter: "blur(0px)", y: [0, -6, 0] }}
            transition={{
              duration: 0.35,
              y: { duration: 2.5, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" },
            }}
          >
            <Gem className="mx-auto size-16 stroke-[1.25] text-primary" aria-hidden={true} />
          </motion.div>
        }
        description="歡迎使用銘印線上訂製。快速導覽將帶您認識各步驟的操作方式。"
      />
    </>
  );
}

export default function ShopTour() {
  const isMobile = useMobileShop();
  const [showWelcome, setShowWelcome] = useState(false);
  const [tourPending, setTourPending] = useState(false);
  const [ready, setReady] = useState(false);
  const completed = readTourCompleted();

  useEffect(() => {
    if (completed) return;

    let attempts = 0;
    const poll = () => {
      attempts += 1;
      if (window.shopTour?.isReady()) {
        setReady(true);
        setShowWelcome(true);
        return true;
      }
      return attempts > 60;
    };

    if (poll()) return;

    const id = window.setInterval(() => {
      if (poll()) window.clearInterval(id);
    }, 250);

    return () => window.clearInterval(id);
  }, [completed]);

  if (completed || !ready) return null;

  return (
    <TourProvider
      isTourCompleted={completed}
      tooltipMode="fixed-bottom"
      onComplete={() => {
        markTourCompleted();
        window.shopTour?.reset();
      }}
    >
      <ShopTourRunner
        isMobile={isMobile}
        showWelcome={showWelcome}
        setShowWelcome={setShowWelcome}
        tourPending={tourPending}
        setTourPending={setTourPending}
      />
    </TourProvider>
  );
}
