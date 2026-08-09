import {
  useEffect,
  useRef,
  useState,
  type ClipboardEvent,
  type KeyboardEvent,
} from "react";
import { Zap } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import {
  CODE_CHAR_RE,
  CODE_LEN,
  unlockReleaseNotes,
} from "@/components/admin/releaseNotesApi";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export default function ReleaseNotesUnlock({ open, onOpenChange }: Props) {
  const [digits, setDigits] = useState<string[]>(() =>
    Array.from({ length: CODE_LEN }, () => ""),
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [shake, setShake] = useState(false);
  const inputsRef = useRef<Array<HTMLInputElement | null>>([]);
  const submittingRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    setDigits(Array.from({ length: CODE_LEN }, () => ""));
    setError("");
    setBusy(false);
    setShake(false);
    submittingRef.current = false;
    const t = window.setTimeout(() => inputsRef.current[0]?.focus(), 40);
    return () => window.clearTimeout(t);
  }, [open]);

  async function submitCode(code: string) {
    if (submittingRef.current) return;
    submittingRef.current = true;
    setBusy(true);
    setError("");
    const result = await unlockReleaseNotes(code);
    if (result.ok) {
      onOpenChange(false);
      window.location.assign("/admin/release-notes");
      return;
    }
    setShake(true);
    setError(result.error || "通行碼錯誤");
    setDigits(Array.from({ length: CODE_LEN }, () => ""));
    setBusy(false);
    submittingRef.current = false;
    window.setTimeout(() => {
      setShake(false);
      inputsRef.current[0]?.focus();
    }, 420);
  }

  function applyAt(index: number, raw: string) {
    const char = raw.slice(-1);
    if (!CODE_CHAR_RE.test(char)) return;
    const next = digits.map((d, i) => (i === index ? char : d));
    setDigits(next);
    if (index < CODE_LEN - 1) {
      inputsRef.current[index + 1]?.focus();
    }
    if (next.every(Boolean)) {
      void submitCode(next.join(""));
    }
  }

  function handlePaste(e: ClipboardEvent<HTMLInputElement>) {
    e.preventDefault();
    const text = e.clipboardData
      .getData("text")
      .replace(/[^0-9A-Za-z]/g, "")
      .slice(0, CODE_LEN);
    if (!text) return;
    const next = Array.from({ length: CODE_LEN }, (_, i) => text[i] || "");
    setDigits(next);
    if (text.length === CODE_LEN) {
      void submitCode(text);
    } else {
      inputsRef.current[Math.min(text.length, CODE_LEN - 1)]?.focus();
    }
  }

  function handleKeyDown(
    index: number,
    e: KeyboardEvent<HTMLInputElement>,
  ) {
    if (e.key === "Backspace") {
      e.preventDefault();
      setDigits((prev) => {
        const next = [...prev];
        if (next[index]) {
          next[index] = "";
        } else if (index > 0) {
          next[index - 1] = "";
          inputsRef.current[index - 1]?.focus();
        }
        return next;
      });
      return;
    }
    if (e.key === "ArrowLeft" && index > 0) {
      e.preventDefault();
      inputsRef.current[index - 1]?.focus();
    }
    if (e.key === "ArrowRight" && index < CODE_LEN - 1) {
      e.preventDefault();
      inputsRef.current[index + 1]?.focus();
    }
    if (e.key === "Enter") {
      const joined = digits.join("");
      if (joined.length === CODE_LEN) void submitCode(joined);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        overlayClassName="bg-black/70 backdrop-blur-[2px]"
        className={cn(
          "max-w-[min(100%-1.5rem,26rem)] gap-0 overflow-hidden rounded-3xl border-white/10 bg-transparent p-0 text-white shadow-2xl sm:max-w-md",
          "[&>button]:text-white/80 [&>button]:hover:text-white [&>button]:opacity-90",
        )}
        aria-describedby={undefined}
      >
        <div className="relative overflow-hidden rounded-3xl">
          {/* Tunnel / gif-style backdrop (CSS motion — no asset dep) */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(59,130,246,0.55)_0%,_transparent_55%),radial-gradient(circle_at_50%_120%,_rgba(15,23,42,0.9)_0%,_#000_70%)]"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 animate-pulse bg-[conic-gradient(from_180deg_at_50%_50%,rgba(37,99,235,0.35),transparent_40%,rgba(0,0,0,0.6),rgba(29,78,216,0.4))] opacity-60"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-gradient-to-b from-blue-600/80 via-blue-800/90 to-black/95"
          />

          <div className="relative z-10 flex flex-col items-center px-6 pt-10 pb-8 sm:px-8">
            <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10 ring-1 ring-white/25 backdrop-blur-md">
              <Zap className="h-7 w-7 fill-white text-white" aria-hidden />
            </div>

            <DialogHeader className="items-center text-center">
              <DialogTitle className="text-xl font-semibold tracking-wide text-white sm:text-2xl">
                輸入通行碼
              </DialogTitle>
              <DialogDescription className="mt-2 max-w-[16rem] text-sm text-white/70">
                長按解鎖後，輸入 6 碼以開啟版本備註編輯頁
              </DialogDescription>
            </DialogHeader>

            <div
              className={cn(
                "mt-8 flex w-full justify-center gap-2 sm:gap-2.5",
                shake && "animate-[release-notes-shake_0.4s_ease-in-out]",
              )}
              role="group"
              aria-label="通行碼 6 碼"
            >
              {digits.map((digit, index) => (
                <input
                  key={index}
                  ref={(el) => {
                    inputsRef.current[index] = el;
                  }}
                  type="text"
                  inputMode="text"
                  autoComplete="one-time-code"
                  maxLength={1}
                  value={digit}
                  disabled={busy}
                  aria-label={`通行碼第 ${index + 1} 碼`}
                  className={cn(
                    "h-12 w-11 rounded-2xl border border-white/20 bg-white/10 text-center text-lg font-semibold text-white shadow-inner outline-none backdrop-blur-md transition",
                    "focus:border-white/50 focus:bg-white/15 focus:ring-2 focus:ring-blue-400/50",
                    "disabled:opacity-60 sm:h-14 sm:w-12",
                  )}
                  onChange={(e) => applyAt(index, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  onPaste={handlePaste}
                  onFocus={(e) => e.target.select()}
                />
              ))}
            </div>

            {error ? (
              <p className="mt-4 text-sm text-red-300" role="alert">
                {error}
              </p>
            ) : (
              <p className="mt-4 text-xs text-white/45">
                {busy ? "驗證中…" : "填滿 6 碼後自動送出"}
              </p>
            )}
          </div>
        </div>

        <style>{`
          @keyframes release-notes-shake {
            0%, 100% { transform: translateX(0); }
            20% { transform: translateX(-6px); }
            40% { transform: translateX(6px); }
            60% { transform: translateX(-4px); }
            80% { transform: translateX(4px); }
          }
        `}</style>
      </DialogContent>
    </Dialog>
  );
}
