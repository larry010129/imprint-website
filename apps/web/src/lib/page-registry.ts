import registryJson from "./page-registry.json";

export type ScriptAsset = {
  src?: string;
  inline?: string;
  type?: string;
  defer?: boolean;
  async?: boolean;
};

export type PageRegistryEntry = {
  route: string;
  template: string;
  title: string;
  description: string;
  canonical_path: string;
  og_title: string | null;
  og_description: string | null;
  og_image: string | null;
  breadcrumbs: [string, string | null][];
  mvc_page: string | null;
  extra_body_class: string | null;
  content_fragment: string | null;
  extra_head_blocks: string[];
  body_key: string;
  layout: "site" | "auth" | "bare";
  main_class: string;
  extra_css: string[];
  extra_scripts: ScriptAsset[];
  head_extras: Array<Record<string, string | undefined>>;
  robots?: string;
  is_share_token?: boolean;
};

const registry = registryJson as PageRegistryEntry[];

const byRoute = new Map(registry.map((entry) => [entry.route, entry]));

export function allPages(): PageRegistryEntry[] {
  return registry;
}

export function getPage(route: string): PageRegistryEntry | undefined {
  return byRoute.get(route);
}

export function siteOrigin(): string {
  return "https://www.imprint-diamond.com";
}
