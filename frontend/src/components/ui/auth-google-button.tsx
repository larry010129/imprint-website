import * as React from "react"

import { Button } from "@/components/ui/button"
import { loginWithGoogleCredential, redirectAfterLogin } from "@/lib/auth-api"
import { cn } from "@/lib/utils"

function GoogleIcon() {
  return (
    <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
      <path d="M1 1h22v22H1z" fill="none" />
    </svg>
  )
}

function AuthSocialButtons({
  isLoading,
  googleClientId,
  onError,
}: {
  isLoading: boolean
  googleClientId?: string
  onError: (message: string) => void
}) {
  const containerRef = React.useRef<HTMLDivElement>(null)
  const [googleReady, setGoogleReady] = React.useState(false)
  const [googleBusy, setGoogleBusy] = React.useState(false)

  React.useEffect(() => {
    if (!googleClientId) return

    const handleCredential = async (response: { credential: string }) => {
      setGoogleBusy(true)
      onError("")
      try {
        const result = await loginWithGoogleCredential(response.credential)
        if (!result.ok || result.data.error) {
          onError(result.data.error || "Google 登入失敗，請再試一次。")
          return
        }
        await redirectAfterLogin()
      } finally {
        setGoogleBusy(false)
      }
    }

    let cancelled = false
    const mountButton = () => {
      const container = containerRef.current
      if (cancelled || !window.google?.accounts?.id || !container) return false

      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: handleCredential,
        auto_select: false,
      })

      const width = Math.min(400, Math.max(240, container.offsetWidth || 320))
      container.replaceChildren()
      window.google.accounts.id.renderButton(container, {
        theme: "outline",
        size: "large",
        width,
        locale: "zh_TW",
        text: "signin_with",
      })
      console.info(
        "[Google Sign-In] If login is blocked, add this origin in Google Cloud Console → Credentials → OAuth client → Authorized JavaScript origins:",
        window.location.origin,
      )
      setGoogleReady(true)
      return true
    }

    if (mountButton()) return () => { cancelled = true }

    let tries = 0
    const timer = window.setInterval(() => {
      tries += 1
      if (mountButton() || tries > 80) window.clearInterval(timer)
    }, 250)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [googleClientId, onError])

  if (!googleClientId) return null

  return (
    <div
      data-slot="auth-social-buttons"
      className={cn(
        "mt-6 w-full",
        (isLoading || googleBusy) && "pointer-events-none opacity-60",
      )}
    >
      {!googleReady && (
        <Button
          type="button"
          variant="outline"
          className="h-12 w-full border-border/50 bg-background/50"
          disabled
        >
          <GoogleIcon />
          使用 Google 登入
        </Button>
      )}
      <div
        ref={containerRef}
        data-slot="auth-google-button"
        className={cn("flex w-full justify-center", !googleReady && "hidden")}
        aria-hidden={!googleReady}
      />
      <p className="mt-3 text-center text-xs leading-relaxed text-muted-foreground">
        使用 Google 登入即表示同意我們依{" "}
        <a href="/privacy.html" className="underline underline-offset-2 hover:text-foreground">
          隱私權政策
        </a>{" "}
        使用您的 Email 與姓名建立會員帳號。電話與地址僅在您同意從 Google 匯入或於帳戶頁自行填寫時蒐集。
      </p>
    </div>
  )
}

export { AuthSocialButtons }
