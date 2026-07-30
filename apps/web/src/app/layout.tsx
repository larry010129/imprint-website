import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    default: "銘印鑽石 IMPRINT DIAMOND｜台灣在地 DNA 紀念鑽石訂製",
    template: "%s",
  },
  description:
    "銘印鑽石｜全台唯一擁有在地DNA鑽石培育實驗室的紀念鑽石品牌。萃取毛髮、骨灰中的元素，於台灣在地培育成專屬紀念鑽石。",
  metadataBase: new URL("https://www.imprint-diamond.com"),
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-Hant-TW" suppressHydrationWarning>
      <head />
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
