export type ReleaseNoteSection = {
  title?: string;
  items: string[];
};

const HEADING_RE = /^#{1,3}\s+/;
const BULLET_RE = /^[-*•]\s+/;

function stripBullet(line: string): string {
  return line.replace(BULLET_RE, "").trim();
}

function stripHeading(line: string): string {
  return line.replace(HEADING_RE, "").trim();
}

/** Group stored note lines into titled sections for display. */
export function parseReleaseNoteSections(notes: string[]): ReleaseNoteSection[] {
  const sections: ReleaseNoteSection[] = [];
  let current: ReleaseNoteSection = { items: [] };

  for (const raw of notes) {
    const line = String(raw ?? "").trim();
    if (!line) continue;

    if (HEADING_RE.test(line)) {
      if (current.title || current.items.length) {
        sections.push(current);
      }
      current = { title: stripHeading(line), items: [] };
      continue;
    }

    current.items.push(stripBullet(line));
  }

  if (current.title || current.items.length) {
    sections.push(current);
  }

  return sections;
}

export function notesHaveSections(notes: string[]): boolean {
  return notes.some((note) => HEADING_RE.test(String(note ?? "").trim()));
}

/** Editor textarea: insert blank lines between sections when structured. */
export function notesToTextarea(notes: string[]): string {
  if (!notes.length) return "";

  if (!notesHaveSections(notes)) {
    return notes.join("\n");
  }

  return parseReleaseNoteSections(notes)
    .map((section) => {
      const lines: string[] = [];
      if (section.title) lines.push(`## ${section.title}`);
      for (const item of section.items) {
        lines.push(`- ${item}`);
      }
      return lines.join("\n");
    })
    .join("\n\n");
}

/** Persist one trimmed line per note; blank lines are section spacing in the editor only. */
export function textareaToNotes(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}
