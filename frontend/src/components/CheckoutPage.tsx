import { useEffect, useId, useMemo, useState, type FormEvent } from "react";
import { CircleCheck } from "lucide-react";
import { useCharacterLimit } from "@/components/hooks/use-character-limit";
import { Alert } from "@/components/ui/heroui-alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import CheckoutItemDetail from "@/components/CheckoutItemDetail";
import { itemMetaLine, type PriceBreakdown, type ShopConfig } from "@/lib/checkout-item-display";
import { fetchSession } from "@/lib/session";
import { cn } from "@/lib/utils";

const NOTE_MAX_LENGTH = 100;

type CartItem = {
  id: string;
  summary_zh?: string | null;
  total_price?: number | null;
  config_json?: ShopConfig | null;
  style_type?: string | null;
  category?: string | null;
  image_url?: string | null;
};

type Breakdown = PriceBreakdown;

type ItemDetail = { item: CartItem; breakdown: Breakdown };

type FulfillmentMethod = "pickup" | "delivery";

const trustPoints = [
  "全台唯一在地 DNA 鑽石培育實驗室",
  "銘印保證卡・GIA／IGI 鑑定保障",
  "封存培育全程的專屬影音紀念盒",
];

function CheckoutHeader() {
  return (
    <header className="checkout-head">
      <h1 className="checkout-title">確認訂單資訊</h1>
      <div className="checkout-notice">
        <Alert status="warning">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Title>送出後仍需專人確認</Alert.Title>
            <Alert.Description>
              線上送出僅代表收到您的訂製申請，並非已下單定案。銘印顧問將與您聯繫，確認規格、交期與報價後，才會進入付款與製作流程。
            </Alert.Description>
          </Alert.Content>
        </Alert>
      </div>
      <p className="checkout-lead">請填寫收件人資訊與取貨方式，確認無誤後送出訂單。</p>
    </header>
  );
}

function apiBase(): string {
  const base = (window as Window & { IMPRINT_API_BASE?: string }).IMPRINT_API_BASE;
  return typeof base === "string" ? base : "";
}

async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<{ ok: boolean; status: number; data: T | null }> {
  const res = await fetch(apiBase() + path, {
    credentials: "include",
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  const text = await res.text();
  let data: T | null = null;
  try {
    data = text ? (JSON.parse(text) as T) : null;
  } catch {
    data = null;
  }
  return { ok: res.ok, status: res.status, data };
}

function formatTwd(n?: number | null): string {
  if (n == null) return "—";
  return "NT$" + Math.round(n).toLocaleString("zh-Hant-TW");
}

function isCartItemId(id: string): boolean {
  // cart_items.id is uuid; reject Number() leftovers like "NaN"
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
}

function parseItemIds(): string[] {
  const params = new URLSearchParams(window.location.search);
  const many = params.get("items");
  const raw = many
    ? many.split(",").map((s) => s.trim()).filter(Boolean)
    : (() => {
        const single = params.get("item");
        return single ? [single.trim()] : [];
      })();
  return raw.filter(isCartItemId);
}

function CheckoutSkeleton() {
  return (
    <div className="checkout-skel" aria-busy="true" aria-label="載入中">
      <CheckoutHeader />
      <div className="checkout-layout">
        <div className="checkout-main">
          <section className="checkout-block">
            <span className="skel-line skel-line--medium" style={{ marginBottom: 16 }} />
            <div className="checkout-skel-item">
              <span className="skel-block skel-block--thumb" />
              <div className="checkout-skel-item-copy">
                <span className="skel-line skel-line--short" />
                <span className="skel-line skel-line--long" style={{ marginTop: 8 }} />
                <span className="skel-line skel-line--medium" style={{ marginTop: 8 }} />
              </div>
            </div>
          </section>
          <section className="checkout-block">
            <span className="skel-line skel-line--medium" style={{ marginBottom: 16 }} />
            <div className="checkout-skel-fields">
              <span className="skel-line skel-line--full" style={{ height: 40 }} />
              <span className="skel-line skel-line--full" style={{ height: 40 }} />
              <span className="skel-line skel-line--full" style={{ height: 40 }} />
            </div>
          </section>
          <section className="checkout-block">
            <span className="skel-line skel-line--medium" style={{ marginBottom: 16 }} />
            <span className="skel-line skel-line--full" style={{ height: 56, marginBottom: 10 }} />
            <span className="skel-line skel-line--full" style={{ height: 56 }} />
          </section>
        </div>
        <aside className="checkout-summary">
          <span className="skel-line skel-line--medium" style={{ marginBottom: 16 }} />
          <span className="skel-line skel-line--full" style={{ marginBottom: 10 }} />
          <span className="skel-line skel-line--full" style={{ marginBottom: 10 }} />
          <span className="skel-line skel-line--short" style={{ marginTop: 16, height: 20 }} />
          <span className="skel-block skel-block--btn" style={{ width: "100%", height: 40, marginTop: 20 }} />
        </aside>
      </div>
    </div>
  );
}

function buildSuccessUrl(orderNumbers?: string[]): string {
  const params = new URLSearchParams();
  const list = (orderNumbers || []).map((s) => s.trim()).filter(Boolean);
  if (list.length === 1) params.set("order", list[0]!);
  else if (list.length > 1) params.set("orders", list.join(","));
  const qs = params.toString();
  return "/success.html" + (qs ? "?" + qs : "");
}

export default function CheckoutPage() {
  const itemIds = useMemo(parseItemIds, []);

  const [items, setItems] = useState<ItemDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [method, setMethod] = useState<FulfillmentMethod>("pickup");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [postal, setPostal] = useState("");
  const [couponInput, setCouponInput] = useState("");
  const [appliedCoupon, setAppliedCoupon] = useState<{
    code: string;
    discountAmount: number;
    total: number;
  } | null>(null);
  const [couponError, setCouponError] = useState<string | null>(null);
  const [couponApplying, setCouponApplying] = useState(false);
  const noteId = useId();
  const {
    value: note,
    characterCount: noteCharacterCount,
    handleChange: handleNoteChange,
    maxLength: noteLimit,
  } = useCharacterLimit({ maxLength: NOTE_MAX_LENGTH });

  useEffect(() => {
    if (!itemIds.length) {
      window.location.href = "/cart.html";
      return;
    }

    let cancelled = false;

    (async () => {
      const resultsPromise = Promise.all(
        itemIds.map((id) =>
          apiFetch<ItemDetail>("/api/cart-item?id=" + encodeURIComponent(id)).catch(() => null)
        )
      );
      const session = await fetchSession();
      if (cancelled) return;
      if (!session) {
        const next = window.location.pathname + window.location.search;
        window.location.href = "/login.html?next=" + encodeURIComponent(next);
        return;
      }
      setName(session.profile?.full_name || "");
      setPhone(session.profile?.phone || "");
      setEmail(session.user.email || "");
      setPostal(session.profile?.shipping_postal || "");
      setCity(session.profile?.shipping_city || "");
      setAddress(session.profile?.shipping_address || "");

      const results = await resultsPromise;
      if (cancelled) return;
      const found = results
        .filter((r) => r?.ok && r.data?.item)
        .map((r) => r?.data as ItemDetail);
      if (!found.length) setError("找不到訂購項目，請重新選購。");
      setItems(found);
      setAppliedCoupon(null);
      setCouponError(null);
      setLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [itemIds]);

  const subtotal = items.reduce((sum, { item, breakdown }) => sum + (breakdown.total ?? item.total_price ?? 0), 0);
  const discountAmount = appliedCoupon?.discountAmount ?? 0;
  const total = appliedCoupon ? appliedCoupon.total : subtotal;

  async function handleApplyCoupon() {
    setCouponError(null);
    const code = couponInput.trim();
    if (!code) {
      setCouponError("請輸入優惠碼");
      return;
    }
    setCouponApplying(true);
    const { status, data } = await apiFetch<{
      ok?: boolean;
      code?: string;
      discountAmount?: number;
      total?: number;
      error?: string;
    }>("/api/coupon/validate", {
      method: "POST",
      body: JSON.stringify({ code, itemIds }),
    });
    setCouponApplying(false);
    if (status === 401) {
      window.location.href = "/login.html";
      return;
    }
    if (!data?.ok || data.discountAmount == null || data.total == null || !data.code) {
      setAppliedCoupon(null);
      setCouponError(data?.error || "優惠碼無效");
      return;
    }
    setAppliedCoupon({
      code: data.code,
      discountAmount: data.discountAmount,
      total: data.total,
    });
    setCouponInput(data.code);
  }

  function clearCoupon() {
    setAppliedCoupon(null);
    setCouponError(null);
    setCouponInput("");
  }

  function showCheckoutError(message: string) {
    setError(message);
    window.requestAnimationFrame(() => {
      document.getElementById("checkout-form-error")?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    });
  }

  function mapCheckoutError(raw?: string | null): string {
    if (!raw) return "送出失敗，請稍後再試";
    const known: Record<string, string> = {
      "cart is empty": "購物車是空的，請返回購物車重新選購",
      "invalid item selection": "訂購項目無效，請返回購物車重新選擇",
      "not signed in": "請先登入後再送出訂單",
      "Internal Server Error": "伺服器發生錯誤，請稍後再試或聯絡客服",
    };
    if (known[raw]) return known[raw];
    if (raw.startsWith("缺少欄位")) {
      return "品項規格不完整，請返回購物車編輯後再送出";
    }
    return raw;
  }

  function readApiError(data: { error?: string; detail?: string | string[] } | null): string | null {
    if (!data) return null;
    if (typeof data.error === "string" && data.error.trim()) return data.error.trim();
    const detail = data.detail;
    if (typeof detail === "string" && detail.trim()) return detail.trim();
    if (Array.isArray(detail) && detail.length) {
      const first = detail.find((part) => typeof part === "string" && part.trim());
      if (typeof first === "string") return first.trim();
    }
    return null;
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    if (!name.trim() || !phone.trim()) {
      showCheckoutError("請填寫姓名與聯絡電話");
      return;
    }
    if (method === "delivery" && (!address.trim() || !city.trim() || !postal.trim())) {
      showCheckoutError("請填寫完整的收件地址");
      return;
    }

    const emailTrimmed = email.trim();
    if (emailTrimmed && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailTrimmed)) {
      showCheckoutError("Email 格式不正確，請修正或清空後再送出");
      return;
    }

    setSubmitting(true);
    try {
      const { status, data } = await apiFetch<{ ok?: boolean; orderNumbers?: string[]; error?: string; detail?: string | string[] }>(
        "/api/cart-checkout",
        {
          method: "POST",
          body: JSON.stringify({
            itemIds,
            customerName: name.trim(),
            customerPhone: phone.trim(),
            customerEmail: emailTrimmed || undefined,
            fulfillmentMethod: method,
            shippingAddress: method === "delivery" ? address.trim() : undefined,
            shippingCity: method === "delivery" ? city.trim() : undefined,
            shippingPostal: method === "delivery" ? postal.trim() : undefined,
            orderNote: note.trim() || undefined,
            couponCode: appliedCoupon?.code || undefined,
          }),
        }
      );

      if (status === 401) {
        const next = window.location.pathname + window.location.search;
        window.location.href = "/login.html?next=" + encodeURIComponent(next);
        return;
      }
      if (data?.ok) {
        window.location.href = buildSuccessUrl(data.orderNumbers);
        return;
      }
      showCheckoutError(mapCheckoutError(readApiError(data)));
    } catch {
      showCheckoutError("網路異常，請稍後再試");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <CheckoutSkeleton />;
  }

  if (!items.length) {
    return (
      <div className="py-12 text-center">
        <p className="text-foreground">{error || "找不到訂購項目"}</p>
        <a className="mt-4 inline-block text-primary underline underline-offset-4" href="/cart.html">
          返回購物車
        </a>
      </div>
    );
  }

  const summaryBlock = (
    <aside className="checkout-summary">
      <h2 className="checkout-summary-title">訂單摘要</h2>
      <ul className="checkout-summary-list">
        {items.map(({ item, breakdown }) => (
          <li key={item.id} className="checkout-summary-item checkout-summary-item--stacked">
            <div className="checkout-summary-item-copy">
              <span className="checkout-summary-item-title">{item.summary_zh || "訂製品項"}</span>
              <span className="checkout-summary-item-meta">
                {itemMetaLine(item.config_json, item.summary_zh)}
              </span>
            </div>
            <span>{formatTwd(breakdown.total ?? item.total_price)}</span>
          </li>
        ))}
      </ul>
      <div className="checkout-coupon">
        <Label htmlFor="checkout-coupon">優惠碼</Label>
        <div className="checkout-coupon-row">
          <Input
            id="checkout-coupon"
            value={couponInput}
            onChange={(e) => {
              setCouponInput(e.target.value);
              if (appliedCoupon) {
                setAppliedCoupon(null);
                setCouponError(null);
              }
            }}
            placeholder="輸入優惠碼"
            disabled={couponApplying || submitting}
            autoComplete="off"
          />
          {appliedCoupon ? (
            <Button type="button" variant="ghost" onClick={clearCoupon} disabled={submitting}>
              清除
            </Button>
          ) : (
            <Button type="button" variant="secondary" onClick={handleApplyCoupon} disabled={couponApplying || submitting}>
              {couponApplying ? "套用中…" : "套用"}
            </Button>
          )}
        </div>
        {couponError && <p className="checkout-coupon-error">{couponError}</p>}
        {appliedCoupon && !couponError && (
          <p className="checkout-coupon-ok">已套用 {appliedCoupon.code}</p>
        )}
      </div>
      {discountAmount > 0 && (
        <div className="checkout-summary-line">
          <span>小計</span>
          <span>{formatTwd(subtotal)}</span>
        </div>
      )}
      {discountAmount > 0 && (
        <div className="checkout-summary-line checkout-summary-line--discount">
          <span>優惠折抵{appliedCoupon ? `（${appliedCoupon.code}）` : ""}</span>
          <span>−{formatTwd(discountAmount)}</span>
        </div>
      )}
      <div className="checkout-summary-total">
        <span>總計</span>
        <span>{formatTwd(total)}</span>
      </div>
      <ul className="checkout-trust">
        {trustPoints.map((point) => (
          <li key={point}>
            <CircleCheck size={14} aria-hidden={true} />
            <span>{point}</span>
          </li>
        ))}
      </ul>
      <p className="checkout-pay-note" role="note">
        此步驟尚未付款。送出後由專人確認規格與報價，確認後才會進行付款。
      </p>
      <div className="checkout-actions checkout-actions--desktop">
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "送出中…" : "確認送出訂單"}
        </Button>
        <Button type="button" variant="ghost" className="w-full" onClick={() => window.history.back()}>
          返回
        </Button>
      </div>
    </aside>
  );

  return (
    <form onSubmit={handleSubmit} noValidate>
      <CheckoutHeader />

      <div className="checkout-layout">
        <div className="checkout-main">
          <section className="checkout-block">
            <h2 className="checkout-block-title">訂製明細</h2>
            {items.map(({ item, breakdown }) => (
              <CheckoutItemDetail key={item.id} item={item} breakdown={breakdown} />
            ))}
          </section>

          <section className="checkout-block">
            <h2 className="checkout-block-title">聯絡資訊</h2>
            <div className="checkout-fields">
              <div className="checkout-field-row">
                <div>
                  <Label htmlFor="checkout-name">
                    姓名<span className="text-red-500">*</span>
                  </Label>
                  <Input id="checkout-name" className="mt-2" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
                </div>
                <div>
                  <Label htmlFor="checkout-phone">
                    聯絡電話<span className="text-red-500">*</span>
                  </Label>
                  <Input id="checkout-phone" className="mt-2" value={phone} onChange={(e) => setPhone(e.target.value)} autoComplete="tel" />
                </div>
              </div>
              <div>
                <Label htmlFor="checkout-email">Email</Label>
                <Input id="checkout-email" type="email" className="mt-2" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
            </div>
          </section>

          <section className="checkout-block">
            <h2 className="checkout-block-title">取貨方式</h2>
            <div className="checkout-fields">
              {(
                [
                  { value: "pickup", title: "到店取件", desc: "新北市三重區福德南路 43 號 1 樓（預約制）" },
                  { value: "delivery", title: "宅配到府", desc: "由專人配送至您指定的地址" },
                ] as const
              ).map((option) => (
                <label
                  key={option.value}
                  className={cn("checkout-option", method === option.value && "is-selected")}
                >
                  <input
                    type="radio"
                    name="fulfillment"
                    className="mt-1"
                    checked={method === option.value}
                    onChange={() => setMethod(option.value)}
                  />
                  <span>
                    <span className="checkout-option-title">{option.title}</span>
                    <span className="checkout-option-desc">{option.desc}</span>
                  </span>
                </label>
              ))}

              {method === "delivery" && (
                <>
                  <div>
                    <Label htmlFor="checkout-address">
                      收件地址<span className="text-red-500">*</span>
                    </Label>
                    <Input id="checkout-address" className="mt-2" value={address} onChange={(e) => setAddress(e.target.value)} autoComplete="street-address" />
                  </div>
                  <div className="checkout-field-row">
                    <div>
                      <Label htmlFor="checkout-city">
                        縣市<span className="text-red-500">*</span>
                      </Label>
                      <Input id="checkout-city" className="mt-2" value={city} onChange={(e) => setCity(e.target.value)} autoComplete="address-level1" />
                    </div>
                    <div>
                      <Label htmlFor="checkout-postal">
                        郵遞區號<span className="text-red-500">*</span>
                      </Label>
                      <Input id="checkout-postal" className="mt-2" value={postal} onChange={(e) => setPostal(e.target.value)} autoComplete="postal-code" />
                    </div>
                  </div>
                </>
              )}
            </div>
          </section>

          <section className="checkout-block">
            <h2 className="checkout-block-title">給銘印鑽石的訊息</h2>
            <div className="space-y-2">
              <Label htmlFor={noteId}>給銘印鑽石的訊息（選填）</Label>
              <Textarea
                id={noteId}
                className="mt-2 min-h-24"
                placeholder="例如刻字內容、預約時段偏好等"
                value={note}
                maxLength={NOTE_MAX_LENGTH}
                onChange={handleNoteChange}
                rows={4}
                aria-describedby={`${noteId}-description`}
              />
              <p
                id={`${noteId}-description`}
                className="mt-2 text-right text-xs text-muted-foreground"
                role="status"
                aria-live="polite"
              >
                尚可輸入 <span className="tabular-nums">{noteLimit - noteCharacterCount}</span> 字
              </p>
            </div>
          </section>

          {error && (
            <p id="checkout-form-error" className="checkout-error" role="alert">
              {error}
            </p>
          )}
        </div>

        {summaryBlock}
      </div>

      <div className="checkout-mobile-bar">
        <div>
          <div className="text-xs text-muted-foreground">總計</div>
          <div className="text-base font-semibold">{formatTwd(total)}</div>
        </div>
        <Button type="submit" disabled={submitting}>
          {submitting ? "送出中…" : "確認送出"}
        </Button>
      </div>
    </form>
  );
}
