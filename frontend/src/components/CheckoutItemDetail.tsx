import type { ReactNode } from "react";
import { Pencil } from "lucide-react";
import {
  breakdownRows,
  itemImageUrl,
  specRows,
  type PriceBreakdown,
  type ShopConfig,
} from "@/lib/checkout-item-display";
import { GirdleEngravingDisplay, looksLikeGirdleEngraving } from "@/lib/girdle-emblems";
import { Button } from "@/components/ui/button";

type CartItem = {
  id: string;
  summary_zh?: string | null;
  config_json?: ShopConfig | null;
  style_type?: string | null;
  category?: string | null;
  image_url?: string | null;
};

type Props = {
  item: CartItem;
  breakdown: PriceBreakdown;
};

function renderSpecValue(label: string, value: string): ReactNode {
  if (label === "腰圍刻字" || looksLikeGirdleEngraving(value)) {
    return <GirdleEngravingDisplay value={value} />;
  }
  return value;
}

function SpecGrid({ rows }: { rows: { label: string; value: string }[] }) {
  return (
    <div className="order-detail-grid">
      {rows.map((row) => (
        <div key={row.label} className="order-detail-item">
          <span className="order-detail-label">{row.label}</span>
          <span className="order-detail-value">{renderSpecValue(row.label, row.value)}</span>
        </div>
      ))}
    </div>
  );
}

export default function CheckoutItemDetail({ item, breakdown }: Props) {
  const config = item.config_json || {};
  const title = item.summary_zh || config.summaryZh || "訂製品項";
  const specs = specRows(config, item.summary_zh);
  const prices = breakdownRows(breakdown);
  const img = itemImageUrl(config, item.style_type, item.image_url);
  const editHref =
    `/shop/calculator/?cart_edit=${encodeURIComponent(item.id)}` +
    `&returnTo=checkout&items=${encodeURIComponent(
      new URLSearchParams(window.location.search).get("items") || item.id
    )}`;

  return (
    <article className="checkout-item-detail">
      <div className="order-detail-layout">
        <div className="order-detail-gallery">
          <div className="order-detail-preview">
            {img ? (
              <img className="order-style-thumb" src={img} alt="" loading="lazy" />
            ) : (
              <span className="order-style-thumb order-style-thumb--empty">💎</span>
            )}
          </div>
          <p className="order-detail-product-name">{title}</p>
          <div className="checkout-item-actions">
            <Button
              asChild
              className="checkout-edit-btn relative w-full ps-12 text-white hover:text-white sm:w-auto"
            >
              <a href={editHref}>
                編輯規格
                <span className="pointer-events-none absolute inset-y-0 start-0 flex w-9 items-center justify-center bg-white/15">
                  <Pencil className="text-white" size={16} strokeWidth={2} aria-hidden="true" />
                </span>
              </a>
            </Button>
          </div>
        </div>
        <div className="order-detail-specs">
          <SpecGrid rows={specs} />
          {prices.length > 0 && (
            <div className="checkout-item-pricing">
              <h3 className="checkout-item-pricing-title">價格明細</h3>
              <SpecGrid rows={prices} />
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
