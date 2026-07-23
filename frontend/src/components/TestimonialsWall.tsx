import { useEffect, useMemo, useState } from "react";
import { TestimonialsRow } from "@/components/ui/testimonials-row";
import { TESTIMONIALS, type Testimonial } from "@/data/testimonials";
import { fetchTestimonialsApi } from "@/lib/content-api";

function excerpt(text: string, max = 88) {
  const plain = text.replace(/^「|」$/g, "");
  return plain.length > max ? `${plain.slice(0, max)}…` : plain;
}

function toWallItems(list: Array<Pick<Testimonial, "name" | "role" | "text" | "image">>) {
  return list.map((item) => ({
    text: `「${excerpt(item.text)}」`,
    name: item.name,
    role: item.role,
    image: item.image,
  }));
}

/** Two horizontal rows scrolling L/R — home + stories. */
export default function TestimonialsWall() {
  const [items, setItems] = useState(TESTIMONIALS);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const api = await fetchTestimonialsApi();
      if (cancelled || !api?.length) return;
      setItems(
        api.map((t, i) => ({
          id: i + 1,
          name: t.name,
          role: t.role || `${t.category}・${t.city}`,
          category: t.category,
          city: t.city,
          text: t.text,
          rating: t.rating || 5,
          image: t.image_url || undefined,
        })),
      );
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const wallRows = useMemo(() => {
    const wall = toWallItems(items);
    const chunk = Math.ceil(wall.length / 2) || 1;
    return [wall.slice(0, chunk), wall.slice(chunk)];
  }, [items]);

  return (
    <div className="flex flex-col gap-3 overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)]">
      <TestimonialsRow testimonials={wallRows[0] || []} duration={32} />
      <TestimonialsRow
        testimonials={wallRows[1] || []}
        duration={36}
        reverse
      />
    </div>
  );
}
