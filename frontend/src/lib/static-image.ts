export type PageImage =
  | { kind: "photo"; src: string; webp?: string; alt: string }
  | { kind: "placeholder"; label: string; alt: string };

export function staticImage(path: string): string {
  if (path.startsWith("/")) return path;
  return `/static/images/${path}`;
}

export function placeholderImage(label: string, alt: string): PageImage {
  return { kind: "placeholder", label, alt };
}

export function photoImage(
  path: string,
  alt: string,
  webpPath?: string
): PageImage {
  return {
    kind: "photo",
    src: staticImage(path),
    webp: webpPath ? staticImage(webpPath) : undefined,
    alt,
  };
}
