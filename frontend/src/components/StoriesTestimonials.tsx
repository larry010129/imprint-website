import { TestimonialsRow } from "@/components/ui/testimonials-row";
import { TESTIMONIALS } from "@/data/testimonials";
import { motion } from "motion/react";

const LINE_URL = "https://lin.ee/ktVBtmx";

function siteRoot() {
  return document.body.dataset.siteRoot ?? "";
}

function excerpt(text: string, max = 88) {
  const plain = text.replace(/^「|」$/g, "");
  return plain.length > max ? `${plain.slice(0, max)}…` : plain;
}

const WALL_ITEMS = TESTIMONIALS.map((item) => ({
  text: `「${excerpt(item.text)}」`,
  name: item.name,
  role: item.role,
}));

const WALL_ROW_CHUNK = Math.ceil(WALL_ITEMS.length / 2);
const WALL_ROWS = [
  WALL_ITEMS.slice(0, WALL_ROW_CHUNK),
  WALL_ITEMS.slice(WALL_ROW_CHUNK, WALL_ROW_CHUNK * 2),
];

export default function StoriesTestimonials() {
  const root = siteRoot();

  return (
    <>
      <section className="relative flex min-h-[320px] items-end overflow-hidden bg-[#2b2320] text-white sm:min-h-[380px]">
        <picture className="absolute inset-0">
          <source
            srcSet={`${root}images/hero/imprint-diamond-pet-memorial-cat.webp`}
            type="image/webp"
          />
          <img
            src={`${root}images/hero/imprint-diamond-pet-memorial-cat.jpg`}
            alt=""
            className="h-full w-full object-cover opacity-50"
            loading="eager"
            decoding="async"
          />
        </picture>
        <div className="absolute inset-0 bg-gradient-to-t from-[#14100d]/90 via-[#14100d]/55 to-[#14100d]/30" />
        <div className="relative z-10 mx-auto px-4 pb-10 pt-16 sm:pb-12">
          <p className="text-sm text-[#c9c0b8]">
            <a href={`${root}index.html`} className="hover:text-[#5ecfcf]">
              首頁
            </a>
            <span className="mx-2 opacity-50">/</span>
            <a href={`${root}about.html`} className="hover:text-[#5ecfcf]">
              關於我們
            </a>
            <span className="mx-2 opacity-50">/</span>
            <span className="text-white">客戶見證</span>
          </p>
          <p className="mt-6 text-xs tracking-[0.35em] text-[#9fe8e8]">
            TESTIMONIALS
          </p>
          <h1
            className="mt-4 max-w-2xl text-3xl font-semibold leading-snug tracking-wide sm:text-4xl md:text-[2.75rem]"
            style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
          >
            思念，在他們手中發著光
          </h1>
          <p className="mt-4 max-w-xl text-sm leading-loose text-[#e5dfd8] sm:text-[15px]">
            每一顆銘印鑽石背後，都是一段真實的故事——來自寵物、摯愛、家人，或送給自己的珍視。
          </p>
        </div>
      </section>

      <section className="border-b border-[#E3DCD3] bg-[#fdfcfa] py-8">
        <div className="mx-auto grid max-w-4xl grid-cols-1 gap-6 px-4 sm:grid-cols-3 sm:gap-8">
          {[
            { value: `${TESTIMONIALS.length}+`, label: "則真實客戶見證" },
            { value: "全台唯一", label: "在地 DNA 鑽石培育實驗室" },
            { value: "可預約", label: "親眼見證鑽石生長過程" },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="text-2xl font-semibold tracking-wide text-[#2b2320]">
                {stat.value}
              </p>
              <p className="mt-1 text-xs tracking-wider text-[#8a817b]">
                {stat.label}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="overflow-hidden bg-background py-14 md:py-20">
        <div className="mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            viewport={{ once: true }}
            className="mx-auto flex max-w-[540px] flex-col items-center justify-center"
          >
            <div className="flex justify-center">
              <div className="rounded-lg border border-[#E3DCD3] px-4 py-1 text-xs tracking-[0.2em] text-[#2b2320]">
                TESTIMONIALS
              </div>
            </div>
            <h2
              className="mt-5 text-center text-2xl font-bold tracking-tight text-[#2b2320] sm:text-3xl md:text-4xl"
              style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
            >
              他們選擇把思念，留成永恆
            </h2>
            <p className="mt-5 text-center text-sm text-[#8a817b]">
              來自不同城市、不同故事的顧客，寫下他們與銘印鑽石相遇的片刻。
            </p>
          </motion.div>

          <div className="mt-10 flex flex-col gap-6 overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
            <TestimonialsRow testimonials={WALL_ROWS[0]} duration={32} />
            <TestimonialsRow testimonials={WALL_ROWS[1]} duration={36} reverse />
          </div>
        </div>
      </section>

      <section className="bg-[#2b2320] px-4 py-20 text-center">
        <div className="mx-auto h-px w-10 bg-[#5ecfcf]" />
        <h2
          className="mt-8 text-2xl font-semibold tracking-wide text-[#f7f4f1] md:text-3xl"
          style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
        >
          您的故事，也值得被好好記住
        </h2>
        <p className="mx-auto mt-5 max-w-md text-sm leading-loose text-[#b8afa8]">
          如果您也在考慮訂製一顆紀念鑽石，
          <br />
          歡迎加入官方 LINE，讓顧問陪您慢慢聊聊。
        </p>
        <a
          href={LINE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-10 inline-block rounded-full bg-[#5ecfcf] px-8 py-3.5 text-sm font-medium tracking-wider text-[#2b2320] transition-colors hover:bg-[#7edede]"
        >
          加入官方 LINE 好友
        </a>
        <p className="mt-6 text-xs text-[#7a716b]">不會頻繁打擾，隨時可以取消</p>
      </section>
    </>
  );
}
