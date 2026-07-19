import type { PageImage } from "@/lib/static-image";
import { photoImage, placeholderImage } from "@/lib/static-image";

export type { PageImage };

const DNA = "dna-process";

export const INTRO = {
  eyebrow: "WHAT IS DNA DIAMOND",
  title: "DNA 鑽石的誕生",
  lead: "從一縷髮絲，到一顆會發光的鑽石——完整的製作過程與品質保障。",
};

export const WHAT_IS = {
  title: "什麼是 DNA 鑽石",
  body: "每一顆 DNA 鑽石，都是一段無可取代的生命印記。我們溫柔萃取毛髮或骨灰中獨一無二的碳元素，在台灣唯一擁有培育技術的實驗室裡，讓思念隨著時間的沉澱，緩緩結晶成永恆的璀璨。",
  callout:
    "銘印鑽石是全台唯一擁有在地 DNA 鑽石培育實驗室的紀念鑽石品牌。您珍視的毛髮與骨灰，不需要經歷國際運送，每一份樣本都以單一客戶、單一培育流程處理。",
  image: photoImage(
    `${DNA}/what-is-dna-diamond-hero.png`,
    "DNA 鑽石意象——將珍視的樣本培育成專屬鑽石"
  ),
};

export const FLOW_TITLE = "時光與情感的淬鍊｜完整製作流程";

export const PROCESS_LEAD_VIDEO = {
  youtubeId: "eBLOrvHosR4",
  title: "DNA 鑽石製作流程影片",
};

/** Factory / lab photo — replace when real asset is ready */
export const LAB_PLACEHOLDER = placeholderImage(
  "實驗室照片即將更新",
  "銘印鑽石在地 DNA 鑽石培育實驗室"
);

export const FLOW_PHASES: Array<{
  id: string;
  title: string;
  description: string;
  image: PageImage;
}> = [
  {
    id: "flow-1",
    title: "樣本萃取",
    description:
      "毛髮約一顆雞蛋大小、骨灰約 3–5 公克，單一客戶、單一培育流程。",
    image: photoImage(
      `${DNA}/collect-bottle.png`,
      "銘印鑽石樣本採集瓶——IMPRINT 專用採集容器"
    ),
  },
  {
    id: "flow-2",
    title: "元素注入・晶化培育",
    description: "元素注入生長設備，讓晶體以自己的節奏，慢慢長成，約需 70–90 天。",
    image: photoImage(
      `${DNA}/crystal-growth.png`,
      "DNA 鑽石晶化培育——實驗室生長設備中的鑽石晶體"
    ),
  },
  {
    id: "flow-3",
    title: "切割拋光",
    description: "依您選擇的克拉數與形狀，精工切磨。",
    image: photoImage(
      `${DNA}/diamond-cutting.png`,
      "DNA 鑽石切割拋光——精工切磨工序"
    ),
  },
  {
    id: "flow-4",
    title: "鑑定保障",
    description: "每顆附銘印保證卡；0.20 克拉以上可代送 GIA 或 IGI 國際鑑定機構出具證書。",
    image: photoImage(
      `${DNA}/certificate-guarantee.png`,
      "銘印保證卡與 GIA／IGI 鑑定證書"
    ),
  },
  {
    id: "flow-5",
    title: "鑲嵌成飾（選擇性）",
    description: "可鑲嵌為戒指、項鍊、耳環或手鍊，材質可選 18K 金、14K 金、9K 金或 PT950 鉑金。",
    image: photoImage(
      "products/ring-classic-solitaire-1.jpg",
      "鑲嵌完成的 DNA 鑽石戒指",
      "products/ring-classic-solitaire-1.webp"
    ),
  },
  {
    id: "flow-6",
    title: "時光封存，璀璨躍然",
    description:
      "當您緩緩打開專屬的淺藍色影音紀念盒，映入眼簾的那顆專屬於您的 DNA 鑽石，不僅是頂級的珠寶工藝，更是將牽絆化為具象的永恆。我們將從樣本到成品的珍貴歷程，與這份光芒一同交付予您。",
    image: photoImage(
      `${DNA}/memorial-media-box.png`,
      "銘印鑽石專屬淺藍色影音紀念盒"
    ),
  },
];

export const SAMPLE_SECTION = {
  title: "需要準備多少樣本",
  body: "毛髮約需一顆雞蛋的大小（或養樂多瓶約 8 分滿）；骨灰約需 3 至 5 公克。我們明白每一縷髮絲、每一份骨灰都無比珍貴。若您手邊的份量不如預期，請無需焦慮。透過官方 LINE 聯繫我們，專屬顧問會細心為您評估各種可能的培育方案，在確認可行之前，您完全不需要先行寄出任何樣本。",
  image: photoImage(
    `${DNA}/sample-quantity-guide.png`,
    "樣本份量示意——毛髮約雞蛋大小或養樂多瓶 8 分滿、骨灰約 3 至 5 公克"
  ),
};

export const LOCAL_SECTION = {
  title: "最近的距離，最深的安心",
  body: "我們深知這份託付的重量。作為全台唯一擁有在地 DNA 鑽石培育實驗室的品牌，您珍視的記憶無需經歷漫長的國際漂流。每一個培育環節，都在您觸手可及的距離裡被悉心呵護；我們非常歡迎貴賓預約蒞臨，親眼見證這份思念逐漸閃耀的過程。",
  image: LAB_PLACEHOLDER,
};

export const ASSURANCE_SECTION = {
  title: "鑑定與保障",
  body: "每顆鑽石皆附銘印保證卡；0.20 克拉以上的鑽石，可代送 GIA 或 IGI 國際鑑定機構出具證書（費用另計）。第三方鑑定為您的珍藏提供客觀保障，也讓這顆鑽石在未來傳承時，有正式的身分證明。",
  image: photoImage(
    `${DNA}/certificate-guarantee.png`,
    "銘印保證卡與第三方鑑定證書"
  ),
};

export const ABOUT_STEPS = [
  {
    no: "01",
    title: "樣本萃取",
    body: "毛髮約一顆雞蛋大小、骨灰約 3–5 公克。每一份樣本都以單一客戶、單一培育流程處理，確保專屬與純粹。",
  },
  {
    no: "02",
    title: "晶化培育",
    body: "元素注入生長設備，讓晶體以自己的節奏慢慢長成。全程於台灣在地實驗室完成，約需 70–90 天。",
  },
  {
    no: "03",
    title: "切割・鑑定・交付",
    body: "依您選擇的克拉數與形狀精工切磨，附銘印保證卡與專屬影音紀念盒，可選鑲嵌為飾品永久珍藏。",
  },
];

export type DnaUspFeature = {
  title: string;
  description: string;
  image: PageImage;
};

export const USP_FEATURES: DnaUspFeature[] = [
  {
    title: "在地實驗室",
    description: "全台唯一擁有在地 DNA 鑽石培育實驗室，樣本不送海外，歡迎預約蒞臨親眼見證鑽石生長。",
    image: LAB_PLACEHOLDER,
  },
  {
    title: "鑑定保障",
    description: "每顆鑽石附銘印保證卡；0.20 克拉以上可代送 GIA 或 IGI 國際鑑定機構出具證書。",
    image: photoImage(
      `${DNA}/certificate-guarantee.png`,
      "GIA／IGI 鑑定與銘印保證卡"
    ),
  },
  {
    title: "影音紀念盒",
    description: "專屬淺藍色影音紀念盒，封存這顆鑽石從樣本到成品的珍貴過程，與光芒一同交付予您。",
    image: photoImage(
      `${DNA}/memorial-media-box.png`,
      "專屬淺藍色影音紀念盒"
    ),
  },
  {
    title: "飾品鑲嵌",
    description: "可鑲嵌為戒指、項鍊、耳環或手鍊，材質可選 18K／14K／9K 金或 PT950 鉑金，依您的故事量身打造。",
    image: photoImage(
      "legacy-live/styles/jewelry-making.jpg",
      "將 DNA 鑽石製作成戒指、項鍊等飾品"
    ),
  },
];
