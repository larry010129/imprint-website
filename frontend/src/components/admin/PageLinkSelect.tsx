import { useId, useMemo, useState } from "react";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export type PageLinkOption = {
  value: string;
  label: string;
};

export const PAGE_LINK_OPTIONS: PageLinkOption[] = [
  { value: "/", label: "首頁" },
  { value: "/shop/calculator/", label: "客製試算" },
  { value: "/price.html", label: "DNA 鑽石價格" },
  { value: "/gold-price.html", label: "台銀金價" },
  { value: "/series.html", label: "系列總覽" },
  { value: "/what-is-dna-diamond.html", label: "DNA 鑽石的誕生" },
  { value: "/faq.html", label: "常見問題" },
  { value: "/about.html", label: "品牌故事" },
  { value: "/stories.html", label: "客戶見證" },
  { value: "/contact.html", label: "聯絡我們" },
  { value: "/track-order.html", label: "查詢訂製進度" },
  { value: "/jewelry/", label: "飾品訂製" },
  { value: "#home-poem", label: "首頁・詩文區塊" },
  { value: "#series", label: "首頁・系列區塊" },
  { value: "https://lin.ee/ktVBtmx", label: "官方 LINE" },
];

export type PageLinkSelectProps = {
  name: string;
  label: string;
  value?: string;
  placeholder?: string;
  options?: PageLinkOption[];
  onChange?: (value: string) => void;
};

const EMPTY = "__none__";

export default function PageLinkSelect({
  name,
  label,
  value = "",
  placeholder = "— 選擇頁面 —",
  options = PAGE_LINK_OPTIONS,
  onChange,
}: PageLinkSelectProps) {
  const id = useId();
  const initial = String(value || "").trim();
  const [current, setCurrent] = useState(initial);

  const items = useMemo(() => {
    const known = new Set(options.map((o) => o.value));
    if (current && !known.has(current) && current !== EMPTY) {
      return [...options, { value: current, label: `目前連結：${current}` }];
    }
    return options;
  }, [options, current]);

  const selectValue = current || EMPTY;

  return (
    <div className="space-y-2" data-admin-root="">
      <Label htmlFor={id}>{label}</Label>
      <input type="hidden" name={name} value={current} />
      <Select
        value={selectValue}
        onValueChange={(next) => {
          const resolved = next === EMPTY ? "" : next;
          setCurrent(resolved);
          onChange?.(resolved);
        }}
      >
        <SelectTrigger id={id} className="w-full">
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={EMPTY}>{placeholder}</SelectItem>
          {items.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
