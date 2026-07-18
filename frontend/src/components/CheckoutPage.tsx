import { useEffect, useMemo, useState, type FormEvent } from "react";
import { CircleCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fetchSession } from "@/lib/session";
import { cn } from "@/lib/utils";

type CartItem = {
  id: string;
  summary_zh?: string | null;
  total_price?: number | null;
};

type Breakdown = {
  total?: number | null;
};

type ItemDetail = { item: CartItem; breakdown: Breakdown };

type FulfillmentMethod = "pickup" | "delivery";

const trustPoints = [
  "全台唯一在地 DNA 鑽石培育實驗室",
  "銘印保證卡・GIA／IGI 鑑定保障",
  "封存培育全程的專屬影音紀念盒",
];

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

function parseItemIds(): string[] {
  const params = new URLSearchParams(window.location.search);
  const many = params.get("items");
  if (many) return many.split(",").map((s) => s.trim()).filter(Boolean);
  const single = params.get("item");
  return single ? [single] : [];
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
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!itemIds.length) {
      window.location.href = "/cart.html";
      return;
    }

    let cancelled = false;

    (async () => {
      const session = await fetchSession();
      if (!session) {
        const next = window.location.pathname + window.location.search;
        window.location.href = "/login.html?next=" + encodeURIComponent(next);
        return;
      }
      if (cancelled) return;
      setName(session.profile?.full_name || "");
      setPhone(session.profile?.phone || "");
      setEmail(session.user.email || "");

      const results = await Promise.all(
        itemIds.map((id) => apiFetch<ItemDetail>("/api/cart-item?id=" + encodeURIComponent(id)))
      );
      if (cancelled) return;
      const found = results
        .filter((r) => r.ok && r.data?.item)
        .map((r) => r.data as ItemDetail);
      if (!found.length) setError("找不到訂購項目，請重新選購。");
      setItems(found);
      setLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [itemIds]);

  const total = items.reduce((sum, { item, breakdown }) => sum + (breakdown.total ?? item.total_price ?? 0), 0);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    if (!name.trim() || !phone.trim()) {
      setError("請填寫姓名與聯絡電話");
      return;
    }
    if (method === "delivery" && (!address.trim() || !city.trim() || !postal.trim())) {
      setError("請填寫完整的收件地址");
      return;
    }

    setSubmitting(true);
    const { status, data } = await apiFetch<{ ok?: boolean; orderNumbers?: string[]; error?: string }>(
      "/api/cart-checkout",
      {
        method: "POST",
        body: JSON.stringify({
          itemIds,
          customerName: name.trim(),
          customerPhone: phone.trim(),
          customerEmail: email.trim() || undefined,
          fulfillmentMethod: method,
          shippingAddress: method === "delivery" ? address.trim() : undefined,
          shippingCity: method === "delivery" ? city.trim() : undefined,
          shippingPostal: method === "delivery" ? postal.trim() : undefined,
          orderNote: note.trim() || undefined,
        }),
      }
    );

    if (status === 401) {
      window.location.href = "/login.html";
      return;
    }
    if (data?.ok) {
      const orderNo = data.orderNumbers?.[0];
      window.location.href = orderNo ? "/success.html?order=" + encodeURIComponent(orderNo) : "/success.html";
      return;
    }
    setSubmitting(false);
    setError(data?.error || "送出失敗，請稍後再試");
  }

  if (loading) {
    return <p className="py-12 text-center text-muted-foreground">載入中…</p>;
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
          <li key={item.id} className="checkout-summary-item">
            <span className="truncate">{item.summary_zh || "訂製品項"}</span>
            <span>{formatTwd(breakdown.total ?? item.total_price)}</span>
          </li>
        ))}
      </ul>
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
    <form onSubmit={handleSubmit}>
      <div className="checkout-layout">
        <div className="checkout-main">
          <section className="checkout-block">
            <h2 className="checkout-block-title">聯絡資訊</h2>
            <div className="checkout-fields">
              <div className="checkout-field-row">
                <div>
                  <Label htmlFor="checkout-name">
                    姓名<span className="text-red-500">*</span>
                  </Label>
                  <Input id="checkout-name" className="mt-2" value={name} onChange={(e) => setName(e.target.value)} required />
                </div>
                <div>
                  <Label htmlFor="checkout-phone">
                    聯絡電話<span className="text-red-500">*</span>
                  </Label>
                  <Input id="checkout-phone" className="mt-2" value={phone} onChange={(e) => setPhone(e.target.value)} required />
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
                    <Input id="checkout-address" className="mt-2" value={address} onChange={(e) => setAddress(e.target.value)} required />
                  </div>
                  <div className="checkout-field-row">
                    <div>
                      <Label htmlFor="checkout-city">
                        縣市<span className="text-red-500">*</span>
                      </Label>
                      <Input id="checkout-city" className="mt-2" value={city} onChange={(e) => setCity(e.target.value)} required />
                    </div>
                    <div>
                      <Label htmlFor="checkout-postal">
                        郵遞區號<span className="text-red-500">*</span>
                      </Label>
                      <Input id="checkout-postal" className="mt-2" value={postal} onChange={(e) => setPostal(e.target.value)} required />
                    </div>
                  </div>
                </>
              )}
            </div>
          </section>

          <section className="checkout-block">
            <h2 className="checkout-block-title">備註</h2>
            <div>
              <Label htmlFor="checkout-note">給銘印鑽石的訊息（選填）</Label>
              <textarea
                id="checkout-note"
                className="mt-2 flex min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="例如刻字內容、預約時段偏好等"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={4}
              />
            </div>
          </section>

          {error && <p className="checkout-error">{error}</p>}
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
