import type { ReactNode } from "react";

/** Same emblem icons as public/js/girdle-engrave.js typing buttons. */
const EMBLEMS: Record<string, { label: string; svg: ReactNode }> = {
  bow: {
    label: "蝴蝶結",
    svg: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 12L4 6v12l8-6z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
        <path d="M12 12l8-6v12l-8-6z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
        <circle cx="12" cy="12" r="1.6" fill="currentColor" />
      </svg>
    ),
  },
  clover: {
    label: "幸運草",
    svg: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <g fill="none" stroke="currentColor" strokeWidth="1.6">
          <circle cx="12" cy="7.5" r="3.6" />
          <circle cx="12" cy="16.5" r="3.6" />
          <circle cx="7.5" cy="12" r="3.6" />
          <circle cx="16.5" cy="12" r="3.6" />
        </g>
      </svg>
    ),
  },
  infinity: {
    label: "無限",
    svg: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M7 9a3 3 0 100 6 5 5 0 004-2 5 5 0 004 2 3 3 0 100-6 5 5 0 00-4 2 5 5 0 00-4-2z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
        />
      </svg>
    ),
  },
  heart: {
    label: "愛心",
    svg: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M12 20s-7-4.6-9.3-9A5 5 0 0112 6a5 5 0 019.3 5c-2.3 4.4-9.3 9-9.3 9z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  hearts: {
    label: "雙愛心",
    svg: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M9 17s-5-3.2-6.6-6.3A3.6 3.6 0 019 8a3.6 3.6 0 016.6 2.7C14 13.8 9 17 9 17z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.4"
        />
        <path
          d="M16.5 19.2s-4.4-2.8-5.7-5.5a3.1 3.1 0 015.7-2.3 3.1 3.1 0 015.7 2.3c-1.3 2.7-5.7 5.5-5.7 5.5z"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.4"
        />
      </svg>
    ),
  },
  paw: {
    label: "肉球",
    svg: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <g fill="currentColor">
          <ellipse cx="12" cy="16.2" rx="5" ry="4" />
          <circle cx="5.6" cy="9.2" r="2" />
          <circle cx="10.4" cy="5.8" r="2" />
          <circle cx="13.6" cy="5.8" r="2" />
          <circle cx="18.4" cy="9.2" r="2" />
        </g>
      </svg>
    ),
  },
  bone: {
    label: "骨頭",
    svg: (
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M4.9 4.9a2.5 2.5 0 013.5 0l.7.7a2.5 2.5 0 010 3.6L7.8 10.6l5.6 5.6 1.3-1.4a2.5 2.5 0 013.6 0l.7.7a2.5 2.5 0 01-3.6 3.5l-.7-.7a2.5 2.5 0 010-3.5l-1.3 1.3-5.6-5.6-1.4 1.3a2.5 2.5 0 01-3.5 0l-.7-.7a2.5 2.5 0 010-3.6z"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  ring: {
    label: "戒圈",
    svg: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="14.5" r="6" fill="none" stroke="currentColor" strokeWidth="1.6" />
        <path d="M9.4 8.6L12 4l2.6 4.6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      </svg>
    ),
  },
};

const LABEL_TO_NAME: Record<string, string> = Object.fromEntries(
  Object.entries(EMBLEMS).map(([name, def]) => [def.label, name])
);

function EmblemToken({ name }: { name: string }) {
  const def = EMBLEMS[name];
  if (!def) return null;
  return (
    <span className="cfg-emblem-token" data-emblem={name} data-label={def.label} aria-label={def.label}>
      {def.svg}
    </span>
  );
}

/** Render stored girdle string like `ABC〔戒圈〕〔肉球〕` with typing icons. */
export function GirdleEngravingDisplay({ value }: { value: string }) {
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
