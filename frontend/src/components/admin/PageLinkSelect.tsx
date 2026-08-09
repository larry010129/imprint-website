import { useEffect, useId, useMemo, useState } from "react";

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
  { value: "/shop/calculator/", label: "Shop 計算器" },
  { value: "/price.html", label: "DNA Diamond 價格" },
  { value: "/gold-price.html", label: "黃金價格" },
  { value: "/series.html", label: "系列總覽" },
  { value: "/series/first-love/", label: "初戀系列" },
  { value: "/series/pet/", label: "寵物系列" },
  { value: "/series/love/", label: "愛情系列" },
  { value: "/series/family/", label: "家庭系列" },
  { value: "/series/heirloom/", label: "傳家系列" },
  { value: "/what-is-dna-diamond.html", label: "什麼是 DNA Diamond" },
  { value: "/faq.html", label: "常見問題" },
  { value: "/about.html", label: "關於我們" },
  { value: "/stories.html", label: "客戶故事" },
  { value: "/contact.html", label: "聯絡我們" },
  { value: "/privacy.html", label: "隱私權政策" },
  { value: "/terms.html", label: "服務條款" },
  { value: "/return-policy.html", label: "退換貨政策" },
  { value: "/track-order.html", label: "查詢訂單" },
  { value: "/jewelry/", label: "珠寶商品" },
  { value: "#home-poem", label: "首頁：品牌詩段" },
  { value: "#series", label: "首頁：系列區塊" },
  { value: "https://lin.ee/ktVBtmx", label: "LINE 官方帳號" },
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
  placeholder = "請選擇頁面",
  options = PAGE_LINK_OPTIONS,
  onChange,
}: PageLinkSelectProps) {
  const id = useId();
  const initial = String(value || "").trim();
  const [current, setCurrent] = useState(initial);

  useEffect(() => {
    setCurrent(initial);
  }, [initial]);

  const items = useMemo(() => {
    const known = new Set(options.map((option) => option.value));
    if (current && !known.has(current) && current !== EMPTY) {
      return [...options, { value: current, label: `目前連結（${current}）` }];
    }
    return options;
  }, [current, options]);

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
        <SelectContent className="z-[210]">
          <SelectItem value={EMPTY}>{placeholder}</SelectItem>
          {items.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
