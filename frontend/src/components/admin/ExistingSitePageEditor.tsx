import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/toast-1";

export type SitePage = {
  route: string;
  title: string;
  content_tab: "page" | "faq" | "testimonials";
};

export type CopySlot = {
  page_key: string;
  slot_key: string;
  kind: "text" | "button";
  label: string;
  text_value: string;
  href: string;
  default_text: string;
  default_href: string;
  is_published: boolean;
};

export type ExistingSitePageEditorProps = {
  page: SitePage;
  api: {
    getCopySlots: () => Promise<{
      slots?: CopySlot[];
      pages?: SitePage[];
      error?: string;
    }>;
    updateCopySlot: (fields: Record<string, unknown>) => Promise<{
      slot?: CopySlot;
      error?: string;
    }>;
  };
  onBack: () => void;
};

export default function ExistingSitePageEditor({
  page,
  api,
  onBack,
}: ExistingSitePageEditorProps) {
  const { showToast } = useToast();
  const [slots, setSlots] = useState<CopySlot[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [device, setDevice] = useState<"desktop" | "mobile">("desktop");
  const [previewTick, setPreviewTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const previewRef = useRef<HTMLIFrameElement>(null);

  const load = useCallback(async () => {
    const result = await api.getCopySlots();
    if (result.error) {
      showToast(String(result.error), "error", "top-right");
      return;
    }
    const pageSlots = (result.slots || []).filter((slot) => slot.page_key === page.route);
    setSlots(pageSlots);
    setSelectedKey((current) =>
      current && pageSlots.some((slot) => slot.slot_key === current)
        ? current
        : pageSlots[0]?.slot_key || null
    );
  }, [api, page.route, showToast]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (event.source !== previewRef.current?.contentWindow) return;
      if (event.data?.source !== "cms-site-inline") return;
      if (event.data.pageKey !== page.route) return;
      if (event.data.type === "select-slot" && event.data.slotKey) {
        setSelectedKey(String(event.data.slotKey));
      }
      if (event.data.type === "select-image") {
        showToast("圖片請在「頁面圖片／首頁圖片」分頁更換", "info", "top-right");
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [page.route, showToast]);

  const selected = useMemo(
    () => slots.find((slot) => slot.slot_key === selectedKey) || null,
    [selectedKey, slots]
  );

  async function save(slot: CopySlot) {
    setBusy(true);
    const result = await api.updateCopySlot({
      pageKey: slot.page_key,
      slotKey: slot.slot_key,
      textValue: slot.text_value,
      href: slot.kind === "button" ? slot.href : "",
      isPublished: slot.is_published,
    });
    setBusy(false);
    if (result.error || !result.slot) {
      showToast(String(result.error || "儲存失敗"), "error", "top-right");
      return;
    }
    setSlots((current) =>
      current.map((item) => (item.slot_key === result.slot!.slot_key ? result.slot! : item))
    );
    setPreviewTick((tick) => tick + 1);
    showToast("頁面內容已儲存", "success", "top-right");
  }

  const previewUrl = `${page.route}${page.route.includes("?") ? "&" : "?"}cms_edit=1&t=${previewTick}`;

  return (
    <div className="cms-editor cms-site-editor">
      <div className="cms-editor__top">
        <button type="button" className="btn-sm" onClick={onBack}>
          ← 返回頁面列表
        </button>
        <strong>{page.title}</strong>
        <span className="cms-editor__site-route">{page.route}</span>
        <a className="btn-sm" href={page.route} target="_blank" rel="noreferrer">
          開啟實際頁面
        </a>
      </div>

      <div className="cms-editor__body">
        <aside className="cms-editor__palette">
          <h3>可編輯內容</h3>
          {page.content_tab !== "page" ? (
            <p className="cms-hint">
              此頁內容由「{page.content_tab === "faq" ? "FAQ" : "見證"}」分頁管理。
            </p>
          ) : null}
          <div className="cms-layers">
            {slots.map((slot) => (
              <button
                key={slot.slot_key}
                type="button"
                className={`cms-layer${selectedKey === slot.slot_key ? " is-active" : ""}`}
                onClick={() => setSelectedKey(slot.slot_key)}
              >
                <span>{slot.kind === "button" ? "按鈕" : "文字"}</span>
                <span>{slot.label}</span>
              </button>
            ))}
            {!slots.length ? <p className="cms-hint">此頁沒有固定文字欄位。</p> : null}
          </div>
        </aside>

        <div className={`cms-editor__canvas cms-editor__canvas--${device}`}>
          <div className="cms-device-toggle">
            <Switch
              name="site-preview-device"
              size="small"
              value={device}
              onValueChange={(next) => {
                if (next === "mobile" || next === "desktop") setDevice(next);
              }}
            >
              <Switch.Control label="手機" value="mobile" />
              <Switch.Control label="電腦" value="desktop" defaultChecked />
            </Switch>
          </div>
          <iframe
            ref={previewRef}
            key={previewUrl}
            title={`${page.title} preview`}
            className="cms-preview-frame"
            src={previewUrl}
          />
        </div>

        <aside className="cms-editor__props">
          <h3>內容設定</h3>
          {selected ? (
            <form
              className="cms-site-slot-form"
              onSubmit={(event) => {
                event.preventDefault();
                void save(selected);
              }}
            >
              <strong>{selected.label}</strong>
              <label className="cms-field">
                <span>文字</span>
                <textarea
                  rows={6}
                  value={selected.text_value}
                  onChange={(event) =>
                    setSlots((current) =>
                      current.map((slot) =>
                        slot.slot_key === selected.slot_key
                          ? { ...slot, text_value: event.target.value }
                          : slot
                      )
                    )
                  }
                />
              </label>
              {selected.kind === "button" ? (
                <label className="cms-field">
                  <span>連結</span>
                  <input
                    value={selected.href}
                    onChange={(event) =>
                      setSlots((current) =>
                        current.map((slot) =>
                          slot.slot_key === selected.slot_key
                            ? { ...slot, href: event.target.value }
                            : slot
                        )
                      )
                    }
                  />
                </label>
              ) : null}
              <label>
                <input
                  type="checkbox"
                  checked={selected.is_published}
                  onChange={(event) =>
                    setSlots((current) =>
                      current.map((slot) =>
                        slot.slot_key === selected.slot_key
                          ? { ...slot, is_published: event.target.checked }
                          : slot
                      )
                    )
                  }
                />{" "}
                啟用自訂值
              </label>
              <button type="submit" className="btn-sm btn-primary" disabled={busy}>
                儲存
              </button>
            </form>
          ) : (
            <p className="cms-hint">點擊預覽中的虛線文字，或從左側選擇。</p>
          )}
        </aside>
      </div>
    </div>
  );
}
