import { useEffect, useState } from "react";

import { useToast } from "@/components/ui/toast-1";

const SLOT_COUNT = 4;
const SLOT_LABELS = ["戒台 1", "戒台 2", "戒台 3", "戒台 4"];

export type RingOption = {
  id: string;
  label: string;
};

export type EngagementRingsApi = {
  getEngagementRings: () => Promise<{
    productIds?: string[];
    options?: RingOption[];
    error?: string;
  }>;
  saveEngagementRings: (fields: { productIds: string[] }) => Promise<{
    productIds?: string[];
    options?: RingOption[];
    ok?: boolean;
    error?: string;
  }>;
};

type SaveState = "idle" | "saving" | "saved" | "error";

function padIds(ids: string[] | undefined): string[] {
  const next = Array.isArray(ids) ? ids.map((id) => String(id || "").trim()) : [];
  while (next.length < SLOT_COUNT) next.push("");
  return next.slice(0, SLOT_COUNT);
}

export default function EngagementRingsEditor({ api }: { api: EngagementRingsApi }) {
  const { showToast } = useToast();
  const [productIds, setProductIds] = useState<string[]>(padIds([]));
  const [options, setOptions] = useState<RingOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [baseline, setBaseline] = useState<string[]>(padIds([]));

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    void api
      .getEngagementRings()
      .then((result) => {
        if (cancelled) return;
        if (result.error) {
          setLoadError(String(result.error));
          return;
        }
        const ids = padIds(result.productIds);
        setProductIds(ids);
        setBaseline(ids);
        setOptions(Array.isArray(result.options) ? result.options : []);
      })
      .catch((error) => {
        if (!cancelled) setLoadError(String(error));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [api]);

  const updateSlot = (index: number, value: string) => {
    setProductIds((current) => current.map((id, i) => (i === index ? value : id)));
    setSaveState("idle");
  };

  const reset = () => {
    setProductIds(baseline);
    setSaveState("idle");
  };

  const save = async () => {
    setSaveState("saving");
    try {
      const result = await api.saveEngagementRings({ productIds: padIds(productIds) });
      if (result.error) throw new Error(String(result.error));
      const ids = padIds(result.productIds);
      setProductIds(ids);
      setBaseline(ids);
      if (Array.isArray(result.options)) setOptions(result.options);
      setSaveState("saved");
      showToast("求婚戒台已儲存", "success", "top-right");
    } catch (error) {
      setSaveState("error");
      showToast(String(error), "error", "top-right");
    }
  };

  const stateLabel =
    saveState === "saving"
      ? "儲存中…"
      : saveState === "saved"
        ? "已儲存"
        : saveState === "error"
          ? "儲存失敗"
          : "";

  return (
    <section className="cms-copy-group">
      <h3 className="cms-copy-group__title">常用求婚／婚戒戒台（4 款）</h3>
      <p className="cms-hint">
        下拉選擇要顯示的戒指商品。前台會顯示商品名稱、說明與上傳的商品圖；「查看款式」連到該商品的試算步驟 2。
      </p>
      {loading ? <p className="cms-hint">載入戒台選項中…</p> : null}
      {loadError ? <p className="cms-msg cms-msg--error">{loadError}</p> : null}
      {!loading && !loadError ? (
        <>
          {SLOT_LABELS.map((label, index) => (
            <label className="cms-field" key={label}>
              <span>{label}</span>
              <select
                value={productIds[index] || ""}
                onChange={(event) => updateSlot(index, event.target.value)}
              >
                <option value="">（未指定 — 顯示預設文案）</option>
                {options.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          ))}
          {!options.length ? (
            <p className="cms-hint">尚無戒指商品。請先在商品管理新增並上架戒指。</p>
          ) : null}
          <div className="cms-copy-card__actions">
            <button type="button" className="btn-sm" onClick={reset}>
              還原
            </button>
            <button
              type="button"
              className="btn-sm btn-primary"
              onClick={() => void save()}
              disabled={saveState === "saving"}
            >
              儲存
            </button>
            <span className={`cms-msg cms-msg--${saveState}`}>{stateLabel}</span>
          </div>
        </>
      ) : null}
    </section>
  );
}
