import { MapPin, MessageCircle, Phone } from "lucide-react";
import {
  FooterBackgroundGradient,
  TextHoverEffect,
} from "@/components/ui/hover-footer";

const MINT = "#5ECFCF";

const dnaLinks = [
  { label: "滿月鑽石", href: "/series/first-love/" },
  { label: "寵物鑽石", href: "/series/pet/" },
  { label: "結髮鑽石", href: "/series/love/" },
  { label: "全家福鑽石", href: "/series/family/" },
  { label: "生命鑽石", href: "/series/heirloom/" },
];

const learnLinks = [
  { label: "什麼是 DNA 鑽石", href: "/what-is-dna-diamond.html" },
  { label: "價格總覽", href: "/price.html" },
  { label: "常見問題", href: "/faq.html" },
  { label: "品牌故事", href: "/about.html" },
  { label: "客戶見證", href: "/stories.html" },
  { label: "時尚珠寶", href: "/jewelry/" },
];

const contactInfo = [
  {
    icon: <MapPin size={18} style={{ color: MINT }} />,
    text: "新北市三重區福德南路 43 號 1 樓（預約制）",
  },
  {
    icon: <Phone size={18} style={{ color: MINT }} />,
    text: "02-2977-0268",
    href: "tel:0229770268",
  },
  {
    icon: <MessageCircle size={18} style={{ color: MINT }} />,
    text: "@imprintdiamond 官方帳號",
    href: "https://lin.ee/ktVBtmx",
    external: true,
  },
];

const socialLinks = [
  {
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
      </svg>
    ),
    label: "Facebook",
    href: "https://www.facebook.com/Imprintdiamond/",
  },
];

export default function HoverFooter() {
  return (
    <footer className="relative m-0 h-fit overflow-hidden rounded-none bg-[#2B2320]/95">
      <div className="relative z-40 mx-auto max-w-7xl p-8 md:p-14">
        <div className="grid grid-cols-1 gap-12 pb-12 md:grid-cols-2 md:gap-8 lg:grid-cols-4 lg:gap-12">
          <div className="flex flex-col space-y-4">
            <div className="flex flex-col space-y-1">
              <span className="text-2xl font-bold tracking-wide text-[#9CEFEF] md:text-3xl">
                銘印鑽石
              </span>
              <span className="text-sm font-semibold tracking-[0.2em] text-[#5ECFCF]">
                IMPRINT DIAMOND
              </span>
            </div>
            <p className="text-sm leading-relaxed text-[#F7F4F1]/80">
              全台唯一擁有在地 DNA 鑽石培育實驗室的紀念鑽石品牌。
              為親人、伴侶、毛孩，把最深的情感，銘印成永恆的珍藏。
            </p>
          </div>

          <div>
            <h4 className="mb-6 text-lg font-semibold text-[#F7F4F1]">DNA 鑽石</h4>
            <ul className="space-y-3 text-sm text-[#F7F4F1]/75">
              {dnaLinks.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    className="transition-colors hover:text-[#5ECFCF]"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="mb-6 text-lg font-semibold text-[#F7F4F1]">瞭解更多</h4>
            <ul className="space-y-3 text-sm text-[#F7F4F1]/75">
              {learnLinks.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    className="transition-colors hover:text-[#5ECFCF]"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="mb-6 text-lg font-semibold text-[#F7F4F1]">聯絡我們</h4>
            <ul className="space-y-4 text-sm text-[#F7F4F1]/75">
              {contactInfo.map((item) => (
                <li key={item.text} className="flex items-start space-x-3">
                  <span className="mt-0.5 shrink-0">{item.icon}</span>
                  {item.href ? (
                    <a
                      href={item.href}
                      className="transition-colors hover:text-[#5ECFCF]"
                      {...(item.external
                        ? { target: "_blank", rel: "noopener noreferrer" }
                        : {})}
                    >
                      {item.text}
                    </a>
                  ) : (
                    <span>{item.text}</span>
                  )}
                </li>
              ))}
            </ul>
            <p className="mt-4">
              <a
                href="/contact.html"
                className="text-xs tracking-wider text-[#5ECFCF] transition-colors hover:text-[#9CEFEF]"
              >
                查看完整聯絡資訊與地圖 →
              </a>
            </p>
          </div>
        </div>

        <hr className="my-8 border-[#5ECFCF]/20" />

        <div className="flex flex-col items-center justify-between space-y-4 text-sm text-[#F7F4F1]/60 md:flex-row md:space-y-0">
          <div className="flex space-x-6">
            {socialLinks.map(({ icon, label, href }) => (
              <a
                key={label}
                href={href}
                aria-label={label}
                target="_blank"
                rel="noopener noreferrer"
                className="transition-colors hover:text-[#5ECFCF]"
              >
                {icon}
              </a>
            ))}
          </div>

          <p className="text-center md:text-right">
            © 2026 心之銘印鑽石有限公司
          </p>
        </div>
      </div>

      <div className="footer-hover-text -mb-36 -mt-52 h-[30rem]">
        <TextHoverEffect text="IMPRINT" className="z-50" />
      </div>

      <FooterBackgroundGradient />
    </footer>
  );
}
