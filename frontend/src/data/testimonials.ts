/** Shared testimonial shape for React UI. Live rows come from `/api/testimonials` (Postgres). */

export type Testimonial = {
  id: number;
  name: string;
  role: string;
  text: string;
  rating: number;
  category: string;
  city: string;
  image?: string;
};
