import * as React from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { AnimatePresence, motion } from "motion/react"
import { ArrowLeft, Eye, EyeOff, Loader2, MailCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Checkbox } from "@/components/ui/checkbox"
import { AuthSocialButtons } from "@/components/ui/auth-google-button"
import { cn } from "@/lib/utils"
import {
  fetchSession,
  getRememberedEmail,
  loginWithPassword,
  redirectAfterLogin,
  requestPasswordReset,
  storeRememberedEmail,
} from "@/lib/auth-api"

enum AuthView {
  SIGN_IN = "sign-in",
  FORGOT_PASSWORD = "forgot-password",
  RESET_SUCCESS = "reset-success",
}

const signInSchema = z.object({
  email: z.string().email("請輸入有效的 Email"),
  password: z.string().min(1, "請輸入密碼"),
  remember: z.boolean(),
})

const forgotPasswordSchema = z.object({
  email: z.string().email("請輸入有效的 Email"),
})

type SignInFormValues = z.infer<typeof signInSchema>
type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>

type AuthProps = React.ComponentProps<"div"> & {
  googleClientId?: string
  registerHref?: string
}

function loginErrorMessage(status: number, data: { error?: string }) {
  if (status === 429) return data.error || "嘗試次數過多，請稍後再試。"
  if (status >= 500) return "伺服器錯誤，請稍後再試或聯絡管理員。"
  return data.error || "Email 或密碼不正確。"
}

function AuthForm({
  onSubmit,
  children,
  className,
}: {
  onSubmit: React.FormEventHandler<HTMLFormElement>
  children: React.ReactNode
  className?: string
}) {
  return (
    <form onSubmit={onSubmit} data-slot="auth-form" className={cn("space-y-6", className)}>
      {children}
    </form>
  )
}

function AuthError({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <div
      data-slot="auth-error"
      className="mb-6 animate-in rounded-lg border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive"
      role="alert"
    >
      {message}
    </div>
  )
}

function AuthSeparator({ text = "或使用" }: { text?: string }) {
  return (
    <div data-slot="auth-separator" className="relative mt-6">
      <div className="absolute inset-0 flex items-center">
        <Separator />
      </div>
      <div className="relative flex justify-center text-xs uppercase">
        <span className="bg-card px-2 text-muted-foreground">{text}</span>
      </div>
    </div>
  )
}

function AuthSignIn({
  googleClientId,
  registerHref,
  onForgotPassword,
}: {
  googleClientId?: string
  registerHref: string
  onForgotPassword: () => void
}) {
  const [formState, setFormState] = React.useState({
    isLoading: false,
    error: null as string | null,
    showPassword: false,
  })

  const remembered = React.useMemo(() => getRememberedEmail(), [])
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<SignInFormValues>({
    resolver: zodResolver(signInSchema),
    defaultValues: { email: remembered, password: "", remember: !!remembered },
  })

  const remember = watch("remember")

  const onSubmit = async (data: SignInFormValues) => {
    setFormState((prev) => ({ ...prev, isLoading: true, error: null }))
    try {
      const result = await loginWithPassword(data.email, data.password, data.remember)
      if (!result.ok || result.data.error) {
        setFormState((prev) => ({
          ...prev,
          error: loginErrorMessage(result.status, result.data),
        }))
        return
      }
      const session = await fetchSession()
      if (!session?.user) {
        setFormState((prev) => ({
          ...prev,
          error: "登入成功但無法保存登入狀態，請確認瀏覽器允許 Cookie 後再試。",
        }))
        return
      }
      storeRememberedEmail(data.email.trim(), data.remember)
      await redirectAfterLogin()
    } catch {
      setFormState((prev) => ({ ...prev, error: "系統連線異常，請稍後再試。" }))
    } finally {
      setFormState((prev) => ({ ...prev, isLoading: false }))
    }
  }

  return (
    <motion.div
      data-slot="auth-sign-in"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className="p-8"
    >
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-semibold text-foreground">歡迎回來</h1>
        <p className="mt-2 text-sm text-muted-foreground">登入後可查詢您的訂製進度，並保留聯絡資料。</p>
      </div>

      <AuthError message={formState.error} />

      <AuthForm onSubmit={handleSubmit(onSubmit)}>
        <div className="space-y-2">
          <Label htmlFor="email">電子郵件</Label>
          <Input
            id="email"
            type="email"
            autoComplete="username"
            placeholder="name@example.com"
            disabled={formState.isLoading}
            className={cn(
              "placeholder:text-muted-foreground/50",
              errors.email && "border-destructive",
            )}
            {...register("email")}
          />
          {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">密碼</Label>
            <Button
              type="button"
              variant="link"
              className="h-auto p-0 text-xs"
              onClick={onForgotPassword}
              disabled={formState.isLoading}
            >
              忘記密碼？
            </Button>
          </div>
          <div className="relative">
            <Input
              id="password"
              type={formState.showPassword ? "text" : "password"}
              autoComplete="current-password"
              disabled={formState.isLoading}
              className={cn("pr-10", errors.password && "border-destructive")}
              {...register("password")}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-0 top-0 h-full"
              onClick={() => setFormState((prev) => ({ ...prev, showPassword: !prev.showPassword }))}
              disabled={formState.isLoading}
              aria-label={formState.showPassword ? "隱藏密碼" : "顯示密碼"}
            >
              {formState.showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
          </div>
          {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
        </div>

        <div className="flex items-center gap-2">
          <Checkbox
            id="remember"
            checked={remember}
            onCheckedChange={(checked) => setValue("remember", checked === true)}
            disabled={formState.isLoading}
          />
          <Label htmlFor="remember" className="text-sm font-normal">
            記住我
          </Label>
        </div>

        <Button type="submit" className="w-full" disabled={formState.isLoading}>
          {formState.isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              登入中…
            </>
          ) : (
            "登入"
          )}
        </Button>
      </AuthForm>

      {googleClientId ? (
        <>
          <AuthSeparator />
          <AuthSocialButtons
            isLoading={formState.isLoading}
            googleClientId={googleClientId}
            onError={(message) => setFormState((prev) => ({ ...prev, error: message || null }))}
          />
        </>
      ) : null}

      <p className="mt-6 text-center text-xs leading-relaxed text-muted-foreground">
        繼續登入即表示您同意我們的{" "}
        <a href="/terms.html" className="underline underline-offset-2 hover:text-foreground">
          服務條款
        </a>{" "}
        與{" "}
        <a href="/privacy.html" className="underline underline-offset-2 hover:text-foreground">
          隱私權政策
        </a>
        。
      </p>

      <p className="mt-4 text-center text-sm text-muted-foreground">
        還沒有帳號？{" "}
        <a href={registerHref} className="font-medium text-primary underline-offset-4 hover:underline">
          註冊
        </a>
      </p>
    </motion.div>
  )
}

function AuthForgotPassword({
  onSignIn,
  onSuccess,
}: {
  onSignIn: () => void
  onSuccess: () => void
}) {
  const [formState, setFormState] = React.useState({
    isLoading: false,
    error: null as string | null,
  })

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  })

  const onSubmit = async (data: ForgotPasswordFormValues) => {
    setFormState({ isLoading: true, error: null })
    try {
      const result = await requestPasswordReset(data.email)
      if (!result.ok && result.status >= 500) {
        setFormState({ isLoading: false, error: "伺服器錯誤，請稍後再試。" })
        return
      }
      onSuccess()
    } catch {
      setFormState({ isLoading: false, error: "系統連線異常，請稍後再試。" })
    } finally {
      setFormState((prev) => ({ ...prev, isLoading: false }))
    }
  }

  return (
    <motion.div
      data-slot="auth-forgot-password"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className="relative p-8"
    >
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="absolute left-4 top-4"
        onClick={onSignIn}
        disabled={formState.isLoading}
      >
        <ArrowLeft className="h-4 w-4" />
        <span className="sr-only">返回</span>
      </Button>

      <div className="mb-8 text-center">
        <h1 className="text-3xl font-semibold text-foreground">重設密碼</h1>
        <p className="mt-2 text-sm text-muted-foreground">輸入 Email，我們會寄送重設連結給您</p>
      </div>

      <AuthError message={formState.error} />

      <AuthForm onSubmit={handleSubmit(onSubmit)}>
        <div className="space-y-2">
          <Label htmlFor="reset-email">電子郵件</Label>
          <Input
            id="reset-email"
            type="email"
            autoComplete="username"
            placeholder="name@example.com"
            disabled={formState.isLoading}
            className={cn(
              "placeholder:text-muted-foreground/50",
              errors.email && "border-destructive",
            )}
            {...register("email")}
          />
          {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
        </div>

        <Button type="submit" className="w-full" disabled={formState.isLoading}>
          {formState.isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              寄送中…
            </>
          ) : (
            "寄送重設連結"
          )}
        </Button>
      </AuthForm>

      <p className="mt-8 text-center text-sm text-muted-foreground">
        想起密碼了？{" "}
        <Button type="button" variant="link" className="h-auto p-0 text-sm" onClick={onSignIn} disabled={formState.isLoading}>
          返回登入
        </Button>
      </p>
    </motion.div>
  )
}

function AuthResetSuccess({ onSignIn }: { onSignIn: () => void }) {
  return (
    <motion.div
      data-slot="auth-reset-success"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className="flex flex-col items-center p-8 text-center"
    >
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
        <MailCheck className="h-8 w-8 text-primary" />
      </div>
      <h1 className="text-2xl font-semibold text-foreground">請查收 Email</h1>
      <p className="mt-2 text-sm text-muted-foreground">若該 Email 已註冊，您會收到重設密碼連結。</p>
      <Button variant="outline" className="mt-6 w-full max-w-xs" onClick={onSignIn}>
        返回登入
      </Button>
    </motion.div>
  )
}

function Auth({ className, googleClientId, registerHref = "/register.html", ...props }: AuthProps) {
  const [view, setView] = React.useState<AuthView>(AuthView.SIGN_IN)

  React.useEffect(() => {
    fetchSession().then((session) => {
      if (session?.user) redirectAfterLogin()
    })
  }, [])

  return (
    <div data-slot="auth" className={cn("mx-auto w-full max-w-md", className)} {...props}>
      <div className="relative overflow-hidden rounded-xl border border-border/50 bg-card/80 shadow-xl backdrop-blur-sm">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-secondary/5" />
        <div className="relative z-10">
          <AnimatePresence mode="wait">
            {view === AuthView.SIGN_IN && (
              <AuthSignIn
                key="sign-in"
                googleClientId={googleClientId}
                registerHref={registerHref}
                onForgotPassword={() => setView(AuthView.FORGOT_PASSWORD)}
              />
            )}
            {view === AuthView.FORGOT_PASSWORD && (
              <AuthForgotPassword
                key="forgot-password"
                onSignIn={() => setView(AuthView.SIGN_IN)}
                onSuccess={() => setView(AuthView.RESET_SUCCESS)}
              />
            )}
            {view === AuthView.RESET_SUCCESS && (
              <AuthResetSuccess key="reset-success" onSignIn={() => setView(AuthView.SIGN_IN)} />
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

export { Auth }
