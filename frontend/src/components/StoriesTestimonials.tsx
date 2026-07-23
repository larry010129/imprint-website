import { useEffect, useState } from "react";
import {
  ImageTestimonialCard,
  MasonryGrid,
} from "@/components/ui/image-testimonial-grid";
import { TESTIMONIALS, type Testimonial } from "@/data/testimonials";
import { fetchTestimonialsApi } from "@/lib/content-api";

const LINE_URL = "https://lin.ee/ktVBtmx";

function columnsForWidth(width: number) {
  if (width < 640) return 1;
  if (width < 1024) return 2;
  if (width < 1280) return 3;
  return 4;
}

export default function StoriesTestimonials() {
  const [items, setItems] = useState<Testimonial[]>(TESTIMONIALS);
  const [columns, setColumns] = useState(3);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const api = await fetchTestimonialsApi();
      if (cancelled || !api?.length) return;
      setItems(
        api.map((t, i) => ({
          id: i + 1,
          name: t.name || "客戶",
          role: t.role || `${t.category || ""}・${t.city || ""}`.replace(/^・|・$/g, ""),
          category: t.category || "",
          city: t.city || "",
          text: t.text || "",
          rating: t.rating || 5,
          image: t.image_url || undefined,
        })),
      );
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onResize = () => setColumns(columnsForWidth(window.innerWidth));
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return (
    <div className="min-h-screen bg-[#f7f4f1]">
      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10 lg:px-8 lg:py-12">
        <MasonryGrid columns={columns} gap={4}>
          {items.map((item, index) => (
            <ImageTestimonialCard
              key={item.id ?? `${item.name}-${index}`}
              index={index}
              name={item.name}
              role={item.role}
              feedback={item.text}
              mainImage={item.image}
            />
          ))}
        </MasonryGrid>
      </section>

      <section className="border-t border-[#E3DCD3] bg-[#fdfcfa] px-4 py-12 text-center">
        <p
          className="text-lg font-semibold tracking-wide text-[#2a2438]"
          style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
        >
          您的故事，也值得被好好記住
        </p>
        <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-[#8a817b]">
          歡迎加入官方 LINE，讓顧問陪您慢慢聊聊。
        </p>
        <a
          href={LINE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-6 inline-block rounded-full bg-[#5ecfcf] px-7 py-3 text-sm font-medium tracking-wider text-[#2b2320] transition-colors hover:bg-[#7edede]"
        >
          加入官方 LINE 好友
        </a>
      </section>
    </div>
  );
}
