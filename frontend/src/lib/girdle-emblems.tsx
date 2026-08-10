import type { ReactNode } from "react";

const EMBLEM_BASE = "/static/images/engraving/";
const EMBLEMS: Record<string, { label: string; image: string }> = {
  catPaw: { label: "貓掌", image: "cat-paw.png" },
  doubleHeart: { label: "雙心", image: "double-heart.png" },
  bowArrow: { label: "弓箭", image: "bow-arrow.png" },
  dogBone: { label: "狗骨", image: "dog-bone.png" },
  clover: { label: "四葉草", image: "clover.png" },
  dogPaw: { label: "狗掌", image: "dog-paw.png" },
  heart: { label: "愛心", image: "heart.png" },
  infinity: { label: "無限", image: "infinity.png" },
};

const LEGACY_RING = "legacyRing";

const LEGACY_LABELS: Record<string, string> = {
  蝴蝶結: "bowArrow",
  雙愛心: "doubleHeart",
  幸運草: "clover",
  肉球: "catPaw",
  骨頭: "dogBone",
  戒圈: LEGACY_RING,
};

const LABEL_TO_NAME: Record<string, string> = Object.fromEntries([
  ...Object.entries(EMBLEMS).map(([name, def]) => [def.label, name]),
  ...Object.entries(LEGACY_LABELS),
]);

function EmblemToken({ name }: { name: string }) {
  if (name === LEGACY_RING) {
    return (
      <span className="cfg-emblem-token" data-emblem={name} data-label="戒圈" aria-label="戒圈">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="14.5" r="6" fill="none" stroke="currentColor" strokeWidth="1.6" />
          <path d="M9.4 8.6L12 4l2.6 4.6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
        </svg>
      </span>
    );
  }
  const def = EMBLEMS[name];
  if (!def) return null;
  return (
    <span className="cfg-emblem-token" data-emblem={name} data-label={def.label} aria-label={def.label}>
      <img src={`${EMBLEM_BASE}${def.image}`} alt="" aria-hidden="true" />
    </span>
  );
}

/** Render stored girdle strings while accepting the legacy emblem labels. */
export function GirdleEngravingDisplay({ value }: { value: string }): ReactNode {
  const parts: ReactNode[] = [];
  const re = /〔([^〕]+)〕|[^〔〕]+/g;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = re.exec(value))) {
    if (match[0].charAt(0) === "〔") {
      const emblemName = LABEL_TO_NAME[match[1]!];
      if (emblemName) parts.push(<EmblemToken key={`e-${i++}`} name={emblemName} />);
      else parts.push(<span key={`t-${i++}`}>{match[0]}</span>);
    } else {
      parts.push(<span key={`t-${i++}`}>{match[0]}</span>);
    }
  }
  return <span className="girdle-engrave-display">{parts}</span>;
}

export function looksLikeGirdleEngraving(value: string): boolean {
  return /〔[^〕]+〕/.test(value);
}
