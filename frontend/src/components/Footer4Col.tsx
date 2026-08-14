/**
 * Adapted Footer4Col reference with imprint data.
 * Not wired into Jinja public pages — reference / optional React use only.
 * Uses plain <a> (no next/link).
 */

import { MapPin, MessageCircle, Phone } from "lucide-react";
import type { SVGProps } from "react";

/** Lucide dropped brand icons (incl. Facebook); keep mark via inline SVG. */
function FacebookIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      {...props}
    >
      <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
    </svg>
  );
}

const data = {
  facebookLink: "https://www.facebook.com/Imprintdiamond/",
  company: {
    nameZh: "銘印鑽石",
    nameEn: "IMPRINT DIAMOND",
    description:
      "全台唯一擁有在地 DNA 鑽石培育實驗室的紀念鑽石品牌。為親人、伴侶、毛孩，把最深的情感，銘印成永恆的珍藏。",
  },
};

const socialLinks = [
  { icon: FacebookIcon, label: "Facebook", href: data.facebookLink },
];

const dnaLinks = [
  { text: "滿月鑽石", href: "/series/first-love/" },
  { text: "寵物鑽石", href: "/series/pet/" },
  { text: "結髮鑽石", href: "/series/love/" },
  { text: "全家福鑽石", href: "/series/family/" },
  { text: "生命鑽石", href: "/series/heirloom/" },
  { text: "銘印鑽石", href: "/series/signature/" },
];

const learnLinks = [
  { text: "什麼是 DNA 鑽石", href: "/what-is-dna-diamond" },
  { text: "鑽石 4C", href: "/diamond-4c" },
  { text: "什麼是培育鑽石", href: "/lab-grown-diamond" },
  { text: "天然 vs 培育／DNA", href: "/diamond-comparison" },
  { text: "價格總覽", href: "/price" },
  { text: "常見問題", href: "/faq" },
  { text: "品牌故事", href: "/about" },
  { text: "客戶見證", href: "/stories" },
  { text: "品牌日誌", href: "/journal" },
  { text: "時尚珠寶", href: "/jewelry/" },
  { text: "求婚／結髮", href: "/jewelry/engagement/" },
];

const contactInfo = [
  {
    icon: MapPin,
    text: "新北市三重區福德南路 43 號 1 樓（預約制）",
    href: "https://maps.app.goo.gl/3Fed2YEpWa8LxQoy9",
    isAddress: true,
    external: true,
  },
  {
    icon: Phone,
    text: "02-2977-0268",
    href: "tel:+886229770268",
  },
  {
    icon: MessageCircle,
    text: "@imprintdiamond 官方帳號",
    href: "https://lin.ee/ktVBtmx",
    external: true,
  },
] as const;

const legalLinks = [
  { label: "退款與退貨政策", href: "/return-policy" },
  { label: "隱私權政策", href: "/privacy" },
  { label: "服務條款", href: "/terms" },
];

export default function Footer4Col() {
  return (
    <footer className="mt-16 w-full place-self-end rounded-t-xl bg-[rgba(43,35,32,0.95)] text-[#F7F4F1]/80">
      <div className="mx-auto max-w-screen-xl px-4 pt-16 pb-6 sm:px-6 lg:px-8 lg:pt-24">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div>
            <div className="flex flex-col gap-1">
              <span className="text-2xl font-bold tracking-wide text-[#9CEFEF]">
                {data.company.nameZh}
              </span>
              <span className="text-sm font-semibold tracking-[0.2em] text-[#5ECFCF]">
                {data.company.nameEn}
              </span>
            </div>

            <p className="mt-6 max-w-md text-sm leading-relaxed text-[#E8E2DB] sm:max-w-xs">
              {data.company.description}
            </p>

            <ul className="mt-8 flex gap-6 md:gap-8">
              {socialLinks.map(({ icon: Icon, label, href }) => (
                <li key={label}>
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#9CEFEF] transition hover:text-[#5ECFCF]"
                  >
                    <span className="sr-only">{label}</span>
                    <Icon className="size-6" aria-hidden="true" />
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 md:grid-cols-3 lg:col-span-2">
            <div>
              <p className="text-lg font-medium text-[#F7F4F1]">DNA 鑽石</p>
              <ul className="mt-8 space-y-4 text-sm">
                {dnaLinks.map(({ text, href }) => (
                  <li key={text}>
                    <a
                      className="text-[#F7F4F1]/75 transition hover:text-[#5ECFCF]"
                      href={href}
                    >
                      {text}
                    </a>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <p className="text-lg font-medium text-[#F7F4F1]">瞭解更多</p>
              <ul className="mt-8 grid grid-cols-2 gap-x-4 gap-y-4 text-sm">
                {learnLinks.map(({ text, href }) => (
                  <li key={text}>
                    <a
                      className="text-[#F7F4F1]/75 transition hover:text-[#5ECFCF]"
                      href={href}
                    >
                      {text}
                    </a>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <p className="text-lg font-medium text-[#F7F4F1]">聯絡我們</p>
              <ul className="mt-8 space-y-4 text-sm">
                {contactInfo.map(({ icon: Icon, text, href, ...rest }) => {
                  const isAddress = "isAddress" in rest && rest.isAddress;
                  const external = "external" in rest && rest.external;
                  return (
                    <li key={text}>
                      <a
                        className="flex items-start gap-1.5 text-[#F7F4F1]/75 transition hover:text-[#5ECFCF]"
                        href={href}
                        {...(external
                          ? { target: "_blank", rel: "noopener noreferrer" }
                          : {})}
                      >
                        <Icon className="mt-0.5 size-5 shrink-0 text-[#9CEFEF]" />
                        {isAddress ? (
                          <address className="flex-1 not-italic">{text}</address>
                        ) : (
                          <span className="flex-1">{text}</span>
                        )}
                      </a>
                    </li>
                  );
                })}
              </ul>
              <p className="mt-4">
                <a
                  href="/contact"
                  className="text-xs tracking-wider text-[#5ECFCF] transition hover:text-[#9CEFEF]"
                >
                  查看完整聯絡資訊與地圖 →
                </a>
              </p>
            </div>
          </div>
        </div>

        <div className="mt-12 border-t border-[#5ECFCF]/20 pt-6">
          <div className="flex flex-col items-center gap-4 text-center sm:flex-row sm:justify-between sm:text-left">
            <p className="text-sm text-[#D4CDC6]">
              © 2026 心之銘印鑽石有限公司
            </p>
            <p className="text-xs text-[#D4CDC6]">
              {legalLinks.map((link, i) => (
                <span key={link.href}>
                  {i > 0 ? " ・ " : null}
                  <a
                    href={link.href}
                    className="text-[#9CEFEF] underline underline-offset-2 transition hover:text-[#C5F7F7]"
                  >
                    {link.label}
                  </a>
                </span>
              ))}
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
