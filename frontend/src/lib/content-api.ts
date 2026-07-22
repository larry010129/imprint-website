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
