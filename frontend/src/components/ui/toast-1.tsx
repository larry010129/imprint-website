"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, AlertTriangle, CircleCheck, Info } from "lucide-react";

type ToastType = "success" | "error" | "warning" | "info";
type ToastPosition = "top-left" | "top-right" | "bottom-left" | "bottom-right" | "center";

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextType {
  showToast: (message: string, type?: ToastType, position?: ToastPosition) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<{ toast: Toast; position: ToastPosition }[]>([]);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const showToast = useCallback(
    (
      message: string,
      type: ToastType = "info",
      position: ToastPosition = "bottom-right"
    ) => {
      const id = Date.now() + Math.floor(Math.random() * 1000);
      setToasts((prev) => [...prev, { toast: { id, message, type }, position }]);
      window.setTimeout(() => {
        setToasts((prev) => prev.filter(({ toast }) => toast.id !== id));
      }, 5000);
    },
    []
  );

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {isMounted
        ? (["top-left", "top-right", "bottom-left", "bottom-right", "center"] as ToastPosition[]).map(
            (position) => (
              <ToastContainer
                key={position}
                toasts={toasts.filter((t) => t.position === position)}
                position={position}
              />
            )
          )
        : null}
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
};

interface ToastContainerProps {
  toasts: { toast: Toast; position: ToastPosition }[];
  position: ToastPosition;
}

const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, position }) => {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const update = () => setIsMobile(window.innerWidth <= 640);
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);

  const adjustedPosition = isMobile
    ? position.startsWith("top")
      ? "top"
      : position === "center"
        ? "center"
        : "bottom"
    : position;

  const getPositionClasses = () => {
    switch (adjustedPosition) {
      case "top-left":
        return "top-4 left-4";
      case "top-right":
        return "top-4 right-4";
      case "bottom-left":
        return "bottom-4 left-4";
      case "bottom-right":
        return "bottom-4 right-4";
      case "top":
        return "top-4 left-1/2 -translate-x-1/2 transform";
      case "bottom":
        return "bottom-4 left-1/2 -translate-x-1/2 transform";
      case "center":
        return "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 transform";
      default:
        return "";
    }
  };

  const getInitialY = () => {
    if (String(adjustedPosition).startsWith("top")) return -50;
    if (adjustedPosition === "center") return 0;
    return 50;
  };

  return (
    <div
      className={`pointer-events-none fixed z-[100] w-full max-w-full space-y-2 px-4 sm:max-w-sm sm:px-0 ${getPositionClasses()}`}
    >
      <AnimatePresence>
        {toasts.map(({ toast }) => (
          <motion.div
            key={toast.id}
            className="pointer-events-auto"
            initial={{ opacity: 0, y: getInitialY() }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: getInitialY() }}
            transition={{ duration: 0.4, ease: "easeInOut" }}
          >
            <ToastComponent {...toast} />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

const ToastComponent: React.FC<Toast> = ({ message, type }) => {
  const typeConfig = {
    success: {
      icon: CircleCheck,
      bgColor: "bg-green-50",
      textColor: "text-green-800",
      borderColor: "border-green-200",
    },
    error: {
      icon: AlertCircle,
      bgColor: "bg-red-50",
      textColor: "text-red-800",
      borderColor: "border-red-200",
    },
    warning: {
      icon: AlertTriangle,
      bgColor: "bg-yellow-50",
      textColor: "text-yellow-800",
      borderColor: "border-yellow-200",
    },
    info: {
      icon: Info,
      bgColor: "bg-blue-50",
      textColor: "text-blue-800",
      borderColor: "border-blue-200",
    },
  };

  const { icon: Icon, bgColor, textColor, borderColor } = typeConfig[type];

  return (
    <div
      className={`${bgColor} ${borderColor} ${textColor} flex max-w-full items-center justify-between rounded-lg border p-4 shadow-lg`}
    >
      <div className="flex items-center space-x-3">
        <Icon className={`${textColor} h-5 w-5 shrink-0`} />
        <p className={`${textColor} font-medium`}>{message}</p>
      </div>
    </div>
  );
};
