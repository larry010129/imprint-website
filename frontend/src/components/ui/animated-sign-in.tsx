import React, { useState, useEffect, useRef, useCallback } from "react";
import { ChevronLeft, Eye, EyeOff, Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";

declare global {
  interface Window {
    imprintAPI?: {
      login: (email: string, password: string) => Promise<{ error?: string }>;
      requestPasswordReset: (email: string) => Promise<{ error?: string }>;
    };
  }
}

const EMAIL_RE =
  /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;

function validateEmail(email: string) {
  return EMAIL_RE.test(email.toLowerCase());
}

function getHomeHref(): string {
  const root = document.body.dataset.siteRoot;
  if (root !== undefined) {
    return `${root}index.html`;
  }
  return "/";
}

const AnimatedSignIn: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isEmailFocused, setIsEmailFocused] = useState(false);
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);
  const [isEmailValid, setIsEmailValid] = useState(true);
  const [isFormSubmitted, setIsFormSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [msgType, setMsgType] = useState<"ok" | "err" | "">("");

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const setMessage = useCallback((text: string, type: "ok" | "err" | "" = "") => {
    setMsg(text);
    setMsgType(type);
  }, []);

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setEmail(value);
    setIsEmailValid(!value || validateEmail(value));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsFormSubmitted(true);
    setMessage("");

    if (!email.trim() || !password) {
      setMessage("請輸入 Email 與密碼。", "err");
      return;
    }
    if (!validateEmail(email.trim())) {
      setMessage("請輸入有效的 Email。", "err");
      return;
    }
    if (!window.imprintAPI) {
      setMessage("系統連線異常，請稍後再試。", "err");
      return;
    }

    setLoading(true);
    const res = await window.imprintAPI.login(email.trim(), password);
    setLoading(false);

    if (res.error) {
      setMessage("登入失敗：Email 或密碼不正確。", "err");
      return;
    }

    setMessage("登入成功，跳轉中…", "ok");
    formRef.current?.classList.add("form-success");
    setTimeout(() => {
      window.location.href = "/account.html";
    }, 500);
  };

  const handleForgotPassword = (e: React.MouseEvent) => {
    e.preventDefault();
    const resetEmail = window.prompt(
      "請輸入您註冊時使用的 Email，我們會寄送重設密碼連結：",
    );
    if (!resetEmail?.trim() || !window.imprintAPI) return;
    window.imprintAPI.requestPasswordReset(resetEmail.trim()).then(() => {
      setMessage(`已寄送重設密碼信件至 ${resetEmail.trim()}，請至信箱查收。`, "ok");
    });
  };

  const toggleDarkMode = () => setIsDarkMode((prev) => !prev);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId = 0;

    const setCanvasSize = () => {
      const rect = container.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;
    };

    setCanvasSize();
    const ro = new ResizeObserver(setCanvasSize);
    ro.observe(container);

    class Particle {
      x = 0;
      y = 0;
      size = 0;
      speedX = 0;
      speedY = 0;
      color = "";

      constructor(w: number, h: number, dark: boolean) {
        this.x = Math.random() * w;
        this.y = Math.random() * h;
        this.size = Math.random() * 3 + 1;
        this.speedX = (Math.random() - 0.5) * 0.5;
        this.speedY = (Math.random() - 0.5) * 0.5;
        this.color = dark
          ? `rgba(156, 239, 239, ${Math.random() * 0.25})`
          : `rgba(94, 207, 207, ${Math.random() * 0.35})`;
      }

      update(w: number, h: number) {
        this.x += this.speedX;
        this.y += this.speedY;
        if (this.x > w) this.x = 0;
        if (this.x < 0) this.x = w;
        if (this.y > h) this.y = 0;
        if (this.y < 0) this.y = h;
      }

      draw(context: CanvasRenderingContext2D) {
        context.fillStyle = this.color;
        context.beginPath();
        context.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        context.fill();
      }
    }

    const particles: Particle[] = [];
    const count = () =>
      Math.min(80, Math.floor((canvas.width * canvas.height) / 12000));

    const initParticles = () => {
      particles.length = 0;
      for (let i = 0; i < count(); i++) {
        particles.push(new Particle(canvas.width, canvas.height, isDarkMode));
      }
    };

    initParticles();

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const p of particles) {
        p.update(canvas.width, canvas.height);
        p.draw(ctx);
      }
      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      ro.disconnect();
      cancelAnimationFrame(animationId);
    };
  }, [isDarkMode]);

  return (
    <div
      ref={containerRef}
      className={`login-container ${isDarkMode ? "dark" : "light"}`}
    >
      <canvas ref={canvasRef} className="particles-canvas" aria-hidden="true" />

      <Button variant="outline" size="sm" className="back-home" asChild>
        <a href={getHomeHref()}>
          <ChevronLeft aria-hidden="true" />
          返回首頁
        </a>
      </Button>

      <button
        type="button"
        className="theme-toggle"
        onClick={toggleDarkMode}
        aria-label={isDarkMode ? "切換淺色模式" : "切換深色模式"}
      >
        {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
      </button>

      <div className="login-card">
        <div className="login-card-inner">
          <div className="login-header">
            <h1>歡迎回來</h1>
            <p>登入後可查詢您的訂製進度，並保留聯絡資料。</p>
          </div>

          <form
            ref={formRef}
            className="login-form"
            onSubmit={handleSubmit}
            noValidate
          >
            <div
              className={`form-field ${
                isEmailFocused || email ? "active" : ""
              } ${!isEmailValid && email ? "invalid" : ""}`}
            >
              <input
                type="email"
                id="login-email"
                name="email"
                value={email}
                onChange={handleEmailChange}
                onFocus={() => setIsEmailFocused(true)}
                onBlur={() => setIsEmailFocused(false)}
                autoComplete="email"
                required
              />
              <label htmlFor="login-email">電子郵件</label>
              {!isEmailValid && email && (
                <span className="error-message">請輸入有效的電子郵件</span>
              )}
            </div>

            <div
              className={`form-field ${
                isPasswordFocused || password ? "active" : ""
              }`}
            >
              <input
                type={showPassword ? "text" : "password"}
                id="login-password"
                name="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onFocus={() => setIsPasswordFocused(true)}
                onBlur={() => setIsPasswordFocused(false)}
                autoComplete="current-password"
                required
              />
              <label htmlFor="login-password">密碼</label>
              <button
                type="button"
                className="toggle-password"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "隱藏密碼" : "顯示密碼"}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>

            <div className="form-options">
              <label className="remember-me">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={() => setRememberMe(!rememberMe)}
                />
                <span className="checkmark" />
                記住我
              </label>

              <button
                type="button"
                className="forgot-password"
                onClick={handleForgotPassword}
              >
                忘記密碼？
              </button>
            </div>

            <button
              type="submit"
              className="login-button"
              disabled={
                loading ||
                (isFormSubmitted && (!email || !password || !isEmailValid))
              }
            >
              {loading ? "登入中…" : "登入"}
            </button>

            {msg && (
              <p
                className={`form-msg ${msgType ? `is-${msgType}` : ""}`}
                role="status"
                aria-live="polite"
              >
                {msg}
              </p>
            )}
          </form>

          <p className="signup-prompt">
            還沒有帳號？
            <a href="/register.html">註冊</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default AnimatedSignIn;
