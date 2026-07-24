import { useEffect, useMemo, useState } from "react";
import { ClipboardList, DoorOpen, KeyRound, LayoutDashboard, ShoppingCart } from "lucide-react";

import { ProfileDropdown, type ProfileMenuItem } from "@/components/ui/profile-dropdown";
import { MembershipComparison } from "@/components/ui/membership-comparison";
import {
  eligibleMembershipOrderCount,
  membershipDisplayLabel,
  membershipUpgradeHint,
  resolveMembershipTier,
} from "@/lib/membership-tiers";
import {
  displayName,
  fetchSession,
  initials,
  logoutSession,
  type Session,
} from "@/lib/session";

type OrderRow = { status?: string | null };

function apiBase(): string {
  const base = (window as Window & { IMPRINT_API_BASE?: string }).IMPRINT_API_BASE;
  return typeof base === "string" ? base : "";
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<{ ok: boolean; status: number; data: T | null }> {
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

function pendingCount(orders: OrderRow[]): number {
  return orders.filter((o) => {
    const status = String(o.status || "").toLowerCase();
    return status === "received" || status === "pending" || status === "processing";
  }).length;
}

export default function ProfilePage() {
  const [loading, setLoading] = useState(true);
  const [session, setSession] = useState<Session | null>(null);
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [editName, setEditName] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editPostal, setEditPostal] = useState("");
  const [editCity, setEditCity] = useState("");
  const [editAddress, setEditAddress] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState(false);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      const [data, orderResult] = await Promise.all([
        fetchSession(),
        apiFetch<{ orders?: OrderRow[] }>("/api/orders").catch(() => null),
      ]);
      if (cancelled) return;
      if (!data) {
        window.location.href = "/login.html?next=" + encodeURIComponent(window.location.pathname);
        return;
      }

      setSession(data);
      setEditName(data.profile?.full_name?.trim() || "");
      setEditPhone(data.profile?.phone?.trim() || "");
      setEditPostal(data.profile?.shipping_postal?.trim() || "");
      setEditCity(data.profile?.shipping_city?.trim() || "");
      setEditAddress(data.profile?.shipping_address?.trim() || "");

      if (orderResult?.ok && orderResult.data?.orders) {
        setOrders(orderResult.data.orders);
      }
      setLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const menuItems = useMemo((): ProfileMenuItem[] => {
    if (!session) return [];
    const items: ProfileMenuItem[] = [
      {
        icon: <ClipboardList className="h-5 w-5" aria-hidden="true" />,
        label: "訂購紀錄",
        href: "/history.html",
      },
      {
        icon: <ShoppingCart className="h-5 w-5" aria-hidden="true" />,
        label: "購物車",
        href: "/cart.html",
      },
      {
        icon: <KeyRound className="h-5 w-5" aria-hidden="true" />,
        label: "重設密碼",
        href: "/reset-password.html",
      },
    ];
    if (session.isAdmin) {
      items.unshift({
        icon: <LayoutDashboard className="h-5 w-5" aria-hidden="true" />,
        label: "管理後台",
        href: "/admin.html",
      });
    }
    items.push({
      icon: <DoorOpen className="h-5 w-5" aria-hidden="true" />,
      label: "登出",
      danger: true,
      onClick: async () => {
        await logoutSession();
        window.location.href = "/login.html";
      },
    });
    return items;
  }, [session]);

  const membershipSummary = useMemo(() => {
    if (!session) return null;
    const eligibleOrderTotal = eligibleMembershipOrderCount(orders);
    const tierId = resolveMembershipTier(session, eligibleOrderTotal);
    return {
      tierId,
      label: membershipDisplayLabel(session, tierId),
      upgradeHint: membershipUpgradeHint(tierId, eligibleOrderTotal),
      pendingOrders: pendingCount(orders),
    };
  }, [orders, session]);

  async function handleSaveProfile() {
    setSaveError(null);
    setSaveOk(false);
    const name = editName.trim();
    const phone = editPhone.trim();
    if (!name) {
      setSaveError("請填寫姓名");
      return;
    }
    if (!phone) {
      setSaveError("請填寫聯絡電話");
      return;
    }

    setSaving(true);
    const { status, data } = await apiFetch<{
      ok?: boolean;
      error?: string;
      profile?: {
        full_name?: string;
        phone?: string;
        shipping_postal?: string | null;
        shipping_city?: string | null;
        shipping_address?: string | null;
      };
    }>("/api/auth/profile", {
      method: "PATCH",
      body: JSON.stringify({
        fullName: name,
        phone,
        shippingPostal: editPostal.trim(),
        shippingCity: editCity.trim(),
        shippingAddress: editAddress.trim(),
      }),
    });
    setSaving(false);

    if (status === 401) {
      window.location.href = "/login.html?next=" + encodeURIComponent(window.location.pathname);
      return;
    }
    if (!data?.ok) {
      setSaveError(data?.error || "儲存失敗，請稍後再試");
      return;
    }

    setSaveOk(true);
    setSession((prev) =>
      prev
        ? {
            ...prev,
            profile: {
              ...prev.profile,
              full_name: data.profile?.full_name ?? name,
              phone: data.profile?.phone ?? phone,
              shipping_postal: data.profile?.shipping_postal ?? (editPostal.trim() || null),
              shipping_city: data.profile?.shipping_city ?? (editCity.trim() || null),
              shipping_address: data.profile?.shipping_address ?? (editAddress.trim() || null),
            },
          }
        : prev,
    );
  }

  if (loading) {
    return (
      <div className="profile-page-state" aria-busy="true" aria-label="載入中">
        <div className="profile-page-skel" />
      </div>
    );
  }

  if (!session) return null;
  if (!membershipSummary) return null;

  const name = displayName(session);
  const email = session.user.email || "";
  const { tierId, label: membershipLabel, upgradeHint, pendingOrders } = membershipSummary;

  return (
    <div className="profile-page-stack mx-auto flex w-full max-w-5xl flex-col gap-8 pb-4">
      <ProfileDropdown
        name={name}
        email={email}
        phone={session.profile?.phone?.trim() || ""}
        roleLabel={membershipLabel}
        membershipTier={membershipLabel}
        membershipTagline="感謝您選擇銘印鑽石，完成訂單即可自動升級會員等級。"
        orderTotal={orders.length}
        orderPending={pendingOrders}
        editName={editName}
        editPhone={editPhone}
        editPostal={editPostal}
        editCity={editCity}
        editAddress={editAddress}
        onEditNameChange={setEditName}
        onEditPhoneChange={setEditPhone}
        onEditPostalChange={setEditPostal}
        onEditCityChange={setEditCity}
        onEditAddressChange={setEditAddress}
        onSaveProfile={handleSaveProfile}
        saving={saving}
        saveError={saveError}
        saveOk={saveOk}
        menuItems={menuItems}
        initials={initials(session)}
      />
      <MembershipComparison currentTierId={tierId} upgradeHint={upgradeHint} />
    </div>
  );
}
