/** Fetch public content APIs with bundled fallbacks. */

export type ApiTestimonial = {
  id: string
  name: string
  role: string
  category: string
  city: string
  text: string
  image_url?: string
  rating: number
  sort_order?: number
}

export type ApiFaqEntry = {
  id: string
  question: string
  answer: string
}

export type ApiFaqCategory = {
  id: string
  title: string
  items: ApiFaqEntry[]
}

export type ApiJournalPost = {
  id: string
  title: string
  body: string
  posted_at: string
  image_url: string | null
  is_archived: boolean
  is_published?: boolean
}

function apiBase(): string {
  const base = (window as Window & { IMPRINT_API_BASE?: string }).IMPRINT_API_BASE
  return typeof base === "string" ? base : ""
}

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(apiBase() + path, { credentials: "same-origin" })
    if (!res.ok) return null
    return (await res.json()) as T
  } catch {
    return null
  }
}

export async function fetchTestimonialsApi(): Promise<ApiTestimonial[] | null> {
  const data = await getJson<{ testimonials?: ApiTestimonial[] }>("/api/testimonials")
  const list = data?.testimonials
  if (!list || !list.length) return null
  return list
}

export async function fetchFaqApi(): Promise<{
  categories: ApiFaqCategory[]
  teaser: ApiFaqEntry[]
} | null> {
  const data = await getJson<{
    categories?: ApiFaqCategory[]
    teaser?: ApiFaqEntry[]
  }>("/api/faq")
  if (!data?.categories?.length) return null
  return {
    categories: data.categories,
    teaser: data.teaser || [],
  }
}

export type JournalPostsPage = {
  posts: ApiJournalPost[]
  page: number
  page_size: number
  total: number
}

export async function fetchJournalPostsApi(options?: {
  page?: number
  pageSize?: number
}): Promise<JournalPostsPage> {
  const page = Math.max(1, options?.page ?? 1)
  const pageSize = Math.max(1, Math.min(100, options?.pageSize ?? 20))
  const qs = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })
  const data = await getJson<{
    posts?: ApiJournalPost[]
    page?: number
    page_size?: number
    total?: number
  }>(`/api/journal/posts?${qs}`)
  const posts = Array.isArray(data?.posts) ? data.posts : []
  return {
    posts,
    page: typeof data?.page === "number" ? data.page : page,
    page_size: typeof data?.page_size === "number" ? data.page_size : pageSize,
    total: typeof data?.total === "number" ? data.total : posts.length,
  }
}
