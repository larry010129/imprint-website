import { useState, type ReactNode } from "react";
import { Check, ChevronUp, Crown } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export type ProfileMenuItem = {
  icon: ReactNode;
  label: string;
  href?: string;
  onClick?: () => void;
  danger?: boolean;
};

export type ProfileDropdownProps = {
  name: string;
  email: string;
  phone: string;
  roleLabel: string;
  membershipTier: string;
  membershipTagline: string;
  orderTotal: number;
  orderPending: number;
  editName: string;
  editPhone: string;
  editPostal: string;
  editCity: string;
  editAddress: string;
  onEditNameChange: (value: string) => void;
  onEditPhoneChange: (value: string) => void;
  onEditPostalChange: (value: string) => void;
  onEditCityChange: (value: string) => void;
  onEditAddressChange: (value: string) => void;
  onSaveProfile: () => void;
  saving?: boolean;
  saveError?: string | null;
  saveOk?: boolean;
  menuItems: ProfileMenuItem[];
  initials: string;
};

export function ProfileDropdown({
  name,
  email,
  phone,
  roleLabel,
  membershipTier,
  membershipTagline,
  orderTotal,
  orderPending,
  editName,
  editPhone,
  editPostal,
  editCity,
  editAddress,
  onEditNameChange,
  onEditPhoneChange,
  onEditPostalChange,
  onEditCityChange,
  onEditAddressChange,
  onSaveProfile,
  saving = false,
  saveError,
  saveOk = false,
  menuItems,
  initials,
}: ProfileDropdownProps) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div className="mx-auto w-full max-w-md overflow-hidden rounded-3xl border border-[#ede7e0] bg-white shadow-[0_12px_40px_rgba(43,35,32,0.08)]">
      <div className="border-b border-[#ede7e0] p-6 transition-colors duration-200 hover:bg-[#fafaf8]">
        <div className="flex items-start gap-4">
          <div className="relative shrink-0 transition-transform hover:scale-[1.04]">
            <Avatar className="h-12 w-12 border border-[#dcf2f2] bg-[#f4fbfb] text-base font-semibold text-[#2b2320]">
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="truncate text-xl font-bold text-[#2b2320]">{name || "會員"}</h2>
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-[#5ecfcf] transition-transform hover:scale-[1.08]">
                <Check className="h-3 w-3 text-white" aria-hidden="true" />
              </span>
            </div>
            <p className="mt-1 text-sm text-[#8a817b]">
              {roleLabel} · {email || "—"}
            </p>
            {phone ? <p className="mt-0.5 text-sm text-[#8a817b]">{phone}</p> : null}
          </div>
          <button
            type="button"
            className="shrink-0 text-[#8a817b] transition-transform hover:scale-[1.08] active:scale-95"
            onClick={() => setIsOpen((open) => !open)}
            aria-expanded={isOpen}
            aria-label={isOpen ? "收合帳戶面板" : "展開帳戶面板"}
          >
            <div className={cn("transition-transform duration-200", !isOpen && "rotate-180")}>
              <ChevronUp className="h-5 w-5" />
            </div>
          </button>
        </div>
      </div>

      {isOpen ? (
        <div>
            <div className="space-y-0 border-b border-[#ede7e0] p-6">
              <div className="mb-4 flex items-center gap-2 text-sm font-semibold tracking-[0.12em] text-[#8a817b]">
                <Crown className="h-4 w-4 text-[#5ecfcf]" aria-hidden="true" />
                會員制度
              </div>
              <div
                className="relative overflow-hidden rounded-2xl p-5 text-[#2b2320] shadow-sm transition-transform hover:scale-[1.01]"
                style={{
                  background:
                    "linear-gradient(135deg, #f4fbfb 0%, #eafcfc 35%, #fff8ef 70%, #f7f4f1 100%)",
                }}
              >
                <div className="mb-4 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs tracking-[0.18em] text-[#8a817b]">IMPRINT MEMBER</p>
                    <p className="mt-1 text-2xl font-bold tracking-wide">{membershipTier}</p>
                  </div>
                  <span className="rounded-full bg-[#5ecfcf] px-3 py-1 text-xs font-semibold text-[#2b2320] shadow-sm">
                    目前等級
                  </span>
                </div>
                <p className="mb-4 text-sm leading-relaxed text-[#5c534e]">{membershipTagline}</p>
                <p className="text-xs text-[#8a817b]">下方表格可查看各等級權益差異與升級條件。</p>
                <div className="mt-5 grid grid-cols-2 gap-3 border-t border-white/70 pt-4 text-center">
                  <div>
                    <p className="text-xs text-[#8a817b]">總訂單</p>
                    <p className="text-lg font-bold">{orderTotal}</p>
                  </div>
                  <div>
                    <p className="text-xs text-[#8a817b]">待處理</p>
                    <p className="text-lg font-bold">{orderPending}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-4 border-b border-[#ede7e0] p-6">
              <div>
                <h3 className="text-sm font-semibold tracking-[0.08em] text-[#2b2320]">聯絡資料</h3>
                <p className="mt-1 text-xs text-[#8a817b]">結帳時會自動帶入，可在此更新姓名與電話。</p>
              </div>
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="profile-full-name">姓名</Label>
                  <Input
                    id="profile-full-name"
                    value={editName}
                    onChange={(e) => onEditNameChange(e.target.value)}
                    autoComplete="name"
                    placeholder="請輸入姓名"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="profile-phone">聯絡電話</Label>
                  <Input
                    id="profile-phone"
                    value={editPhone}
                    onChange={(e) => onEditPhoneChange(e.target.value)}
                    autoComplete="tel"
                    placeholder="請輸入電話"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-4 border-b border-[#ede7e0] p-6">
              <div>
                <h3 className="text-sm font-semibold tracking-[0.08em] text-[#2b2320]">寄送地址</h3>
                <p className="mt-1 text-xs text-[#8a817b]">選擇宅配時會自動帶入；可留空，結帳時再填亦可。</p>
              </div>
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="profile-postal">郵遞區號</Label>
                  <Input
                    id="profile-postal"
                    value={editPostal}
                    onChange={(e) => onEditPostalChange(e.target.value)}
                    autoComplete="postal-code"
                    inputMode="numeric"
                    placeholder="例：106"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="profile-city">縣市</Label>
                  <Input
                    id="profile-city"
                    value={editCity}
                    onChange={(e) => onEditCityChange(e.target.value)}
                    autoComplete="address-level1"
                    placeholder="例：台北市大安區"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="profile-address">詳細地址</Label>
                  <Input
                    id="profile-address"
                    value={editAddress}
                    onChange={(e) => onEditAddressChange(e.target.value)}
                    autoComplete="street-address"
                    placeholder="路名、巷弄、樓層"
                  />
                </div>
              </div>
              {saveError ? <p className="text-sm text-[#c0392b]">{saveError}</p> : null}
              {saveOk ? <p className="text-sm text-[#3e8e62]">已儲存帳戶資料</p> : null}
              <Button
                type="button"
                className="w-full rounded-full bg-[#2b2320] text-white hover:bg-[#2b2320]"
                disabled={saving}
                onClick={onSaveProfile}
              >
                {saving ? "儲存中…" : "儲存帳戶資料"}
              </Button>
            </div>

            <div className="space-y-1 border-b border-[#ede7e0] p-4">
              {menuItems.map((item) =>
                item.href ? (
                  <a
                    key={item.label}
                    href={item.href}
                    className={cn(
                      "flex items-center rounded-xl p-3 text-sm transition-all duration-200 hover:pl-5 active:scale-[.98]",
                      item.danger
                        ? "text-[#c0392b] hover:bg-[#fdecea]"
                        : "text-[#2b2320] hover:bg-[#f7f4f1]",
                    )}
                  >
                    <span className="mr-3">{item.icon}</span>
                    <span>{item.label}</span>
                  </a>
                ) : (
                  <button
                    key={item.label}
                    type="button"
                    onClick={item.onClick}
                    className={cn(
                      "flex w-full items-center rounded-xl p-3 text-left text-sm transition-all duration-200 hover:pl-5 active:scale-[.98]",
                      item.danger
                        ? "text-[#c0392b] hover:bg-[#fdecea]"
                        : "text-[#2b2320] hover:bg-[#f7f4f1]",
                    )}
                  >
                    <span className="mr-3">{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                ),
              )}
            </div>

            <div className="flex items-center justify-between p-4 text-sm text-[#8a817b]">
              <span className="font-medium text-[#2b2320]">銘印鑽石 IMPRINT</span>
              <span>會員中心</span>
            </div>
        </div>
      ) : null}
    </div>
  );
}
