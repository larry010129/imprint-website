import { useEffect, useRef, useState, type ReactNode } from "react";
import DnaInfoFigure from "@/components/DnaInfoFigure";
import {
  ABOUT_STEPS,
  ASSURANCE_SECTION,
  FLOW_PHASES,
  FLOW_TITLE,
  LOCAL_SECTION,
  PROCESS_LEAD_VIDEO,
  SAMPLE_SECTION,
  USP_FEATURES,
  WHAT_IS,
} from "@/data/dna-diamond-content";

const SECTIONS = [
  { id: "intro", label: "什麼是 DNA 鑽石" },
  { id: "process", label: "完整製作流程" },
  { id: "sample", label: "需要準備多少樣本" },
  { id: "local", label: "在地實驗室" },
  { id: "assurance", label: "鑑定與保障" },
  { id: "promise", label: "四大保障" },
] as const;

const KEY_FACTS = [
  { label: "樣本份量", value: "毛髮約雞蛋大小、骨灰 3–5 公克" },
  { label: "培育週期", value: "約 70–90 天" },
  { label: "鑑定保障", value: "銘印保證卡；0.20 克拉以上可代送 GIA／IGI" },
  { label: "培育地點", value: "全台唯一在地 DNA 鑽石培育實驗室" },
  { label: "樣本處理", value: "單一客戶、單一培育流程" },
  { label: "飾品鑲嵌", value: "戒指、項鍊、耳環、手鍊（18K／14K／9K／PT950）" },
];

function siteRoot() {
  const base = document.body.dataset.siteRoot ?? "";
  return base.endsWith("/") ? base : base ? `${base}/` : "/";
}

function InfoToc({ activeSection }: { activeSection: string }) {
  const root = siteRoot();
  return (
    <nav className="dna-info-toc">
      <p className="mb-4 text-[10px] tracking-[0.28em] uppercase text-[#8a817b]">本頁目錄</p>
      <ul className="space-y-0">
        {SECTIONS.map((s) => (
          <li key={s.id}>
            <a
              href={`${root}what-is-dna-diamond.html#${s.id}`}
              className={`block border-l-2 py-2 pl-4 text-sm transition-all duration-200 ${
                activeSection === s.id
                  ? "border-[#5ecfcf] font-medium text-[#5ecfcf]"
                  : "border-[#e3dcd3] text-[#8a817b] hover:border-[#5ecfcf]/40 hover:text-[#2b2320]"
              }`}
            >
              {s.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function SectionTitle({ en, zh }: { en: string; zh: string }) {
  return (
    <div className="mb-8 border-b border-[#e3dcd3] pb-4">
      <p className="mb-1 text-[10px] tracking-[0.22em] uppercase text-[#8a817b]">{en}</p>
      <h2
        className="text-2xl font-semibold text-[#2b2320]"
        style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
      >
        {zh}
      </h2>
    </div>
  );
}

function Prose({ children }: { children: ReactNode }) {
  return (
    <p className="text-sm leading-[2] text-[#5c534e] md:text-[15px]">{children}</p>
  );
}

function SplitVideo({ youtubeId, title }: { youtubeId: string; title: string }) {
  return (
    <div className="dna-info-video dna-info-video--split">
      <iframe
        src={`https://www.youtube.com/embed/${youtubeId}`}
        title={title}
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        referrerPolicy="strict-origin-when-cross-origin"
        allowFullScreen
      />
    </div>
  );
}

function SplitSection({
  body,
  image,
}: {
  body: ReactNode;
  image: (typeof WHAT_IS)["image"];
}) {
  return (
    <div className="dna-info-split">
      <div className="min-w-0">{body}</div>
      <DnaInfoFigure image={image} variant="split" />
    </div>
  );
}

function ProcessSteps() {
  return (
    <div className="space-y-0">
      {FLOW_PHASES.map((step, i) => (
        <div key={step.id} className="relative grid grid-cols-[auto_1fr] gap-5 pb-10 last:pb-0 md:gap-6">
          {i < FLOW_PHASES.length - 1 && (
            <div className="absolute bottom-0 left-4 top-9 w-px bg-[#e3dcd3]" aria-hidden />
          )}
          <div className="relative z-10 flex flex-col items-center pt-0.5">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-full border-2 border-[#5ecfcf] bg-[#fdfcfa]">
              <span
                className="text-xs font-medium text-[#5ecfcf]"
                style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
            </div>
          </div>
          <div className="min-w-0">
            <h3
              className="mb-3 text-base font-semibold text-[#2b2320]"
              style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
            >
              第{["一", "二", "三", "四", "五", "六"][i]}步　{step.title}
            </h3>
            <div className="dna-info-step-row">
              <Prose>{step.description}</Prose>
              <DnaInfoFigure image={step.image} variant="step" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function DnaDiamondPage() {
  const root = siteRoot();
  const [activeSection, setActiveSection] = useState<string>("intro");
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActiveSection(entry.target.id);
        });
      },
      { rootMargin: "-20% 0px -70% 0px" }
    );
    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observerRef.current?.observe(el);
    });
    return () => observerRef.current?.disconnect();
  }, []);

  return (
    <div className="dna-info-page bg-[#fdfcfa] text-[#2b2320]">
      <div className="dna-info-layout">
        <aside className="dna-info-toc-wrap">
          <InfoToc activeSection={activeSection} />
        </aside>

        <main className="dna-info-main min-w-0 space-y-16 md:space-y-20">
          <section id="intro">
            <SectionTitle en="Introduction" zh={WHAT_IS.title} />
            <div className="space-y-5">
              <SplitSection body={<Prose>{WHAT_IS.body}</Prose>} image={WHAT_IS.image} />
              <div className="overflow-hidden rounded-md border border-[#e3dcd3]">
                <div className="border-b border-[#e3dcd3] bg-[#f7f4f1] px-5 py-3">
                  <p className="text-xs font-medium text-[#2b2320]">重要基本資訊</p>
                </div>
                <div className="dna-info-facts grid divide-y divide-[#e3dcd3]">
                  {KEY_FACTS.map((item) => (
                    <div key={item.label} className="px-5 py-4">
                      <p className="mb-1 text-[10px] tracking-wide text-[#8a817b]">{item.label}</p>
                      <p className="text-sm font-medium text-[#2b2320]">{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-md border border-[#dcf2f2] bg-[#f4fbfb] px-5 py-4 text-sm leading-[1.95] text-[#3a7a7a]">
                {WHAT_IS.callout}
              </div>
            </div>
          </section>

          <section id="process">
            <SectionTitle en="Manufacturing Process" zh={FLOW_TITLE} />
            <div className="dna-info-split mb-8">
              <Prose>
                從樣本萃取到鑲嵌交付，每一顆 DNA 鑽石都經過慎重對待的完整流程。以下依序說明六個主要階段，全程於台灣在地實驗室完成。
              </Prose>
              <SplitVideo
                youtubeId={PROCESS_LEAD_VIDEO.youtubeId}
                title={PROCESS_LEAD_VIDEO.title}
              />
            </div>
            <ProcessSteps />
          </section>

          <section id="sample">
            <SectionTitle en="Sample Requirements" zh={SAMPLE_SECTION.title} />
            <SplitSection body={<Prose>{SAMPLE_SECTION.body}</Prose>} image={SAMPLE_SECTION.image} />
          </section>

          <section id="local">
            <SectionTitle en="Local Laboratory" zh={LOCAL_SECTION.title} />
            <SplitSection body={<Prose>{LOCAL_SECTION.body}</Prose>} image={LOCAL_SECTION.image} />
          </section>

          <section id="assurance">
            <SectionTitle en="Quality & Certification" zh={ASSURANCE_SECTION.title} />
            <SplitSection body={<Prose>{ASSURANCE_SECTION.body}</Prose>} image={ASSURANCE_SECTION.image} />
            <div className="mt-8 flex flex-wrap gap-3">
              <a
                href={`${root}#series`}
                className="inline-flex items-center rounded-full bg-[#9cefef] px-6 py-3 text-sm tracking-wider text-[#2b2320] transition hover:bg-[#b7f4f4]"
              >
                探索您的專屬紀念｜五大訂製系列
              </a>
              <a
                href={`${root}faq.html`}
                className="inline-flex items-center rounded-full border border-[#2b2320] px-6 py-3 text-sm tracking-wider text-[#2b2320] transition hover:bg-[#2b2320] hover:text-white"
              >
                與顧問聊聊您的故事
              </a>
            </div>
          </section>

          <section id="promise">
            <SectionTitle en="Our Promise" zh="四大保障，讓您安心託付" />
            <Prose>
              DNA 鑽石是萃取毛髮或骨灰中的元素，注入鑽石生長設備中，經晶化培育而成的專屬個人化鑽石——不是複製品，而是從您珍視的樣本中，真實培育而成。
            </Prose>
            <div className="mt-8 space-y-0 divide-y divide-[#efe9e3] border-y border-[#efe9e3]">
              {ABOUT_STEPS.map((step) => (
                <div key={step.no} className="grid grid-cols-[auto_1fr] gap-5 py-5">
                  <span
                    className="shrink-0 pt-0.5 text-sm tracking-wider text-[#5ecfcf]"
                    style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
                  >
                    {step.no}
                  </span>
                  <div>
                    <h3
                      className="text-base font-semibold text-[#2b2320]"
                      style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
                    >
                      {step.title}
                    </h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-[#5c534e]">{step.body}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="dna-info-usp mt-8 grid gap-4">
              {USP_FEATURES.map((feature) => (
                <div key={feature.title} className="dna-info-usp-card overflow-hidden rounded-md border border-[#e3dcd3]">
                  <DnaInfoFigure image={feature.image} variant="usp" />
                  <div className="p-5">
                    <h3
                      className="text-sm font-semibold tracking-[0.06em] text-[#2b2320]"
                      style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
                    >
                      {feature.title}
                    </h3>
                    <p className="mt-2 text-xs leading-[1.85] text-[#5c534e]">{feature.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="border-t border-[#e3dcd3] pt-8">
            <p className="text-xs leading-relaxed text-[#8a817b]">
              完整培育週期約 <b className="font-medium text-[#5ecfcf]">70–90 天</b>｜歡迎
              <a href={`${root}contact.html`} className="mx-1 text-[#5ecfcf] hover:underline">
                預約蒞臨實驗室
              </a>
              親眼見證
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
