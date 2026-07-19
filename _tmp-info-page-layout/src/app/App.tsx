import { useState, useEffect, useRef } from "react";

const sections = [
  { id: "intro", label: "DNA鑽石簡介" },
  { id: "science", label: "科學原理" },
  { id: "process", label: "製作流程" },
  { id: "quality", label: "品質與鑑定" },
  { id: "comparison", label: "與天然鑽石比較" },
  { id: "care", label: "保養與注意事項" },
  { id: "faq", label: "常見問題" },
];

const steps = [
  {
    num: "第一步",
    en: "DNA Sample Collection",
    title: "DNA樣本採集",
    content: [
      "採集工作由居家自行完成，無需前往實驗室。我們提供標準化的採集套組，內含採樣工具、密封保存容器、中文操作說明書及預付運費回寄袋。",
      "可接受的樣本類型包括：帶有毛囊的頭髮（8–12根）、指甲片段（修剪後的正常指甲，約0.5克）或乾燥血液點片。毛髮採集是最常用的方式，輕輕拔取即可，過程無痛。",
      "樣本採集完成後，裝入密封容器，以回寄袋寄回指定實驗室。建議於採集後48小時內寄出，避免高溫或潮濕環境，確保樣本完整性。"
    ],
    note: "注意：每份訂單需提供同一個人的樣本，不接受混合樣本。"
  },
  {
    num: "第二步",
    en: "DNA Analysis & Carbon Extraction",
    title: "DNA分析與碳元素萃取",
    content: [
      "實驗室收到樣本後，生物化學家首先進行樣本鑑定，確認樣本品質與數量是否足夠。樣本通過驗收後，進入DNA萃取流程。",
      "萃取過程採用標準分子生物學程序：先以裂解液破壞細胞膜，釋放出DNA，再經過離心純化去除蛋白質與細胞碎片，最終取得高純度的DNA溶液。",
      "DNA分子中富含碳氫鍵，是優質的碳源。純化後的DNA經過高溫灰化處理，有機物中的氫、氧、氮等元素以氣體形式揮發，留下高純度的碳殘留物。此碳殘留物再經過精煉純化，使碳純度達到99.99%以上，成為鑽石培育的原料。",
    ],
    note: "萃取完成後，剩餘的DNA樣本依生物廢棄物處理規範銷毀，不作任何其他用途保存。"
  },
  {
    num: "第三步",
    en: "Diamond Crystal Growth",
    title: "鑽石晶體培育",
    content: [
      "根據客戶選擇，採用HPHT（高壓高溫法）或CVD（化學氣相沉積法）進行晶體培育。兩種方法均可生產高品質鑽石，各有其適合的應用場景（詳見〈科學原理〉章節）。",
      "HPHT製程：將碳原料與金屬催化劑放置於特製腔體，施加5–6 GPa壓力，加熱至1,400–1,600°C。碳原子以預置的種晶為核心，以面心立方晶格結構逐層堆疊，歷經數週形成鑽石晶體。",
      "CVD製程：在低壓真空腔體內通入含碳氣體（甲烷CH₄與氫氣H₂混合），以微波能量將氣體電離為電漿。電漿中的碳原子沉積至加熱至700–900°C的種晶表面，一層一層累積成鑽石晶體。"
    ],
    note: "培育週期因目標克拉數而異：0.5克拉約需6–8週，1克拉以上可能需要10–14週。"
  },
  {
    num: "第四步",
    en: "Rough Stone Assessment",
    title: "原石評估與規劃",
    content: [
      "培育完成的原石由寶石師進行初步評估，檢視晶體的形態、尺寸、淨度分布及潛在的切割方向。此階段會以三維掃描儀建立原石的精確數位模型。",
      "利用數位模型進行切割模擬，計算不同切割方案下的重量保留率與成品品質。最終選定的方案需在最大化成品克拉數與最優化視覺品質之間取得平衡。",
      "評估報告完成後，寶石師將以書面及影像形式通知客戶，說明原石狀態、建議切割形式及預估成品參數，客戶確認後方進行下一步。"
    ],
    note: "若原石品質未達標準，將通知客戶並重新安排培育，不另外收費。"
  },
  {
    num: "第五步",
    en: "Precision Cutting & Polishing",
    title: "精密切割與拋光",
    content: [
      "由資深寶石切割師以手工操作精密切割機台進行加工。鑽石的硬度為10莫氏，只有鑽石可以切割鑽石，因此切割工具均以鑽石粉末製成。",
      "切割分為以下階段：劈割或鋸割（確定主要分割面）→ 成形（粗磨成目標輪廓）→ 刻面切割（以精確角度切出各個刻面）→ 拋光（以漸進細緻的鑽石粉研磨至鏡面光澤）。",
      "標準圓形明亮式切割共有57–58個刻面，每個刻面的角度與大小均依幾何計算精確執行，目的是讓進入鑽石的光線產生全內反射，以最大化亮度（Brilliance）、火彩（Fire）與閃爍（Scintillation）。"
    ],
    note: "切割過程中的損耗通常為原石重量的40–60%，此為正常範圍，不影響最終品質。"
  },
  {
    num: "第六步",
    en: "Grading & Certification",
    title: "鑑定分級與發證",
    content: [
      "成品鑽石送交GIA（美國寶石學院）或IGI（國際寶石學院）進行獨立鑑定。鑑定師在不知悉鑽石來源的情況下，依據國際4C標準對鑽石進行完整評估。",
      "鑑定書內容包含：鑽石的克拉重量、顏色等級（D至Z）、淨度等級（FL至I3）、切割等級（Excellent至Poor）、螢光反應、精確的尺寸測量，以及「Lab-Grown」起源標示。鑽石腰部會以雷射刻上與鑑定書對應的唯一識別號碼。",
      "鑑定完成後，鑽石與鑑定書一同以保險快遞方式寄送至客戶指定地址，附上DNA鑽石製作報告及品質保證書。"
    ],
    note: "GIA及IGI鑑定書均為國際認可文件，可作為珠寶保險及轉售的正式憑證。"
  },
];

const faqData = [
  {
    q: "DNA鑽石算是「真正的鑽石」嗎？",
    a: "是的。DNA鑽石在化學組成（純碳sp3晶格結構）、物理性質（硬度10莫氏）及光學特性（折射率2.417）上與天然鑽石完全相同。GIA等機構將其歸類為「Lab-Grown Diamond（實驗室培育鑽石）」，是鑽石的一個子類別，而非仿品或替代品。任何標準鑽石測試儀均無法從中區分。"
  },
  {
    q: "整個製作流程需要多長時間？",
    a: "從收到DNA樣本至最終交付，全程通常需要4–6個月。各階段時間分配大致如下：樣本分析與碳萃取約2–3週；晶體培育依克拉數不同需6–14週；評估與切割約3–4週；鑑定與發證約2–3週；包裝與運送約1週。我們在每個關鍵節點均會主動通知您進度。"
  },
  {
    q: "採集多少樣本才夠？",
    a: "帶有毛囊的頭髮8–12根，或正常修剪的指甲片段約0.3–0.5克，通常已足夠萃取所需碳量。若樣本量不足，我們會在評估後第一時間聯絡您補件，不會直接進入下一步。"
  },
  {
    q: "DNA資料會被保留或分析嗎？",
    a: "不會。您的DNA樣本只用於鑽石製作所需的碳萃取，萃取完成後即依生物廢棄物規範銷毀。我們不建立基因資料庫，不對基因序列進行分析或解碼，不與任何第三方分享遺傳資訊。"
  },
  {
    q: "鑽石的顏色可以選擇嗎？",
    a: "HPHT製程可生產黃色、橙色至近無色的鑽石，顏色深淺取決於培育條件；CVD製程主要生產無色至近無色鑽石。若需特定顏色，可討論輻射處理選項（於培育後以輻射改色，GIA會在鑑定書上標注處理方式）。完全無色（D–F色）的DNA鑽石可以做到，但需額外時間。"
  },
  {
    q: "鑽石是否可以鑲嵌成珠寶？",
    a: "可以。裸鑽交付後，您可以選擇我們的客製鑲嵌服務，或自行委託信任的珠寶商處理。鑽石的物理特性與天然鑽石完全相同，任何珠寶商均可正常進行鑲嵌工作，無需特殊設備或技術。"
  },
  {
    q: "如果培育失敗或成品不符預期怎麼辦？",
    a: "若培育過程中原石品質未達標準，我們將重新安排培育，不另外收費。最終成品的克拉數可能與目標有±0.05克拉的差異，此為行業正常範圍。若成品存在影響美觀的重大瑕疵，我們將與您協商解決方案，包括重新切割或重新培育。"
  },
];

function TOC({ activeSection }: { activeSection: string }) {
  return (
    <nav className="sticky top-8">
      <p className="text-xs tracking-[0.2em] uppercase text-muted-foreground mb-4" style={{ fontFamily: "'DM Mono', monospace" }}>
        本頁目錄
      </p>
      <ul className="space-y-0">
        {sections.map((s) => (
          <li key={s.id}>
            <a
              href={`#${s.id}`}
              className={`block py-2 text-sm border-l-2 pl-4 transition-all duration-200 ${
                activeSection === s.id
                  ? "border-accent text-accent font-medium"
                  : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/30"
              }`}
              style={{ fontFamily: "'Noto Sans TC', sans-serif" }}
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
    <div className="mb-8 pb-4 border-b border-border">
      <p className="text-xs tracking-[0.18em] text-muted-foreground uppercase mb-1" style={{ fontFamily: "'DM Mono', monospace" }}>
        {en}
      </p>
      <h2 className="text-2xl font-semibold text-foreground" style={{ fontFamily: "'Noto Serif TC', serif" }}>
        {zh}
      </h2>
    </div>
  );
}

function FAQItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-border last:border-0">
      <button
        className="w-full text-left py-5 flex items-start justify-between gap-4 group"
        onClick={() => setOpen(!open)}
      >
        <span className="text-sm font-medium text-foreground leading-relaxed" style={{ fontFamily: "'Noto Serif TC', serif" }}>
          {q}
        </span>
        <span className={`text-muted-foreground mt-0.5 shrink-0 transition-transform duration-200 ${open ? "rotate-180" : ""}`}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 5l5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </button>
      <div className={`overflow-hidden transition-all duration-300 ${open ? "max-h-96 pb-5" : "max-h-0"}`}>
        <p className="text-sm text-muted-foreground leading-[1.95]" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
          {a}
        </p>
      </div>
    </div>
  );
}

export default function App() {
  const [activeSection, setActiveSection] = useState("intro");
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
    sections.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observerRef.current?.observe(el);
    });
    return () => observerRef.current?.disconnect();
  }, []);

  return (
    <div className="min-h-screen bg-background" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>

      {/* Article header */}
      <header className="border-b border-border bg-card">
        <div className="max-w-6xl mx-auto px-6 py-10">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-6" style={{ fontFamily: "'DM Mono', monospace" }}>
            <span>產品知識</span>
            <span className="opacity-40">/</span>
            <span className="text-foreground">DNA鑽石</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-semibold text-foreground mb-4 max-w-2xl leading-snug" style={{ fontFamily: "'Noto Serif TC', serif" }}>
            DNA鑽石完整指南：原理、製程與品質說明
          </h1>
          <p className="text-muted-foreground max-w-2xl leading-relaxed text-sm md:text-base" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
            本文完整說明DNA鑽石的科學原理、從樣本採集到成品交付的六個製作步驟、品質評估標準，以及與天然鑽石的詳細比較，協助您在購買前充分了解這項技術與產品。
          </p>
          <div className="mt-6 flex flex-wrap gap-6 text-xs text-muted-foreground" style={{ fontFamily: "'DM Mono', monospace" }}>
            <span>閱讀時間：約 12 分鐘</span>
            <span className="text-border">|</span>
            <span>最後更新：2024年12月</span>
            <span className="text-border">|</span>
            <span>語言：繁體中文</span>
          </div>
        </div>
      </header>

      {/* Body: TOC + Content */}
      <div className="max-w-6xl mx-auto px-6 py-12 grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-14">

        {/* TOC sidebar */}
        <aside className="hidden lg:block">
          <TOC activeSection={activeSection} />
        </aside>

        {/* Main content */}
        <main className="min-w-0 space-y-20">

          {/* 1. 簡介 */}
          <section id="intro">
            <SectionTitle en="Introduction" zh="DNA鑽石簡介" />
            <div className="prose-content space-y-5">
              <p className="text-foreground/85 leading-[2] text-sm md:text-base" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
                DNA鑽石（DNA Diamond），又稱「生命鑽石」或「紀念鑽石」，是一種以人類DNA中萃取的碳元素為原料，透過實驗室培育技術生長而成的真實鑽石。其化學組成、晶體結構與物理特性均與天然鑽石完全一致，並非仿品或替代品。
              </p>
              <p className="text-foreground/85 leading-[2] text-sm md:text-base" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
                這項技術的核心概念，在於人體DNA分子中含有大量的碳原子——而碳，正是鑽石的唯一組成元素。科學家透過生物化學方法萃取DNA中的碳，再以現代實驗室技術令這些碳原子在受控環境中結晶為鑽石，整個過程可在數個月內完成，而非天然鑽石所需的數億年。
              </p>
              <p className="text-foreground/85 leading-[2] text-sm md:text-base" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
                從應用場景來看，DNA鑽石最常被用於：為已故親人留下永久的生命紀念、製作獨一無二的個人化珠寶、或作為特殊里程碑的紀念品。由於每顆DNA鑽石均來自特定個人的遺傳物質，世界上不存在兩顆來源相同的DNA鑽石。
              </p>

              {/* 快速資訊框 */}
              <div className="mt-8 border border-border rounded-sm overflow-hidden">
                <div className="bg-muted px-5 py-3 border-b border-border">
                  <p className="text-xs font-medium text-foreground" style={{ fontFamily: "'DM Mono', monospace" }}>重要基本資訊</p>
                </div>
                <div className="grid sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-border">
                  {[
                    { label: "化學成分", value: "純碳（C），sp3混成晶格" },
                    { label: "硬度", value: "10 莫氏（最高等級）" },
                    { label: "鑑定分類", value: "Lab-Grown Diamond（GIA/IGI）" },
                    { label: "全程製作時間", value: "約 4–6 個月" },
                    { label: "可採用的樣本", value: "毛髮、指甲、乾燥血液點片" },
                    { label: "培育技術", value: "HPHT 或 CVD（依需求選擇）" },
                  ].map((item) => (
                    <div key={item.label} className="px-5 py-4">
                      <p className="text-xs text-muted-foreground mb-1" style={{ fontFamily: "'DM Mono', monospace" }}>{item.label}</p>
                      <p className="text-sm text-foreground font-medium" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* 2. 科學原理 */}
          <section id="science">
            <SectionTitle en="The Science" zh="科學原理" />
            <div className="space-y-6">
              <h3 className="text-base font-semibold text-foreground" style={{ fontFamily: "'Noto Serif TC', serif" }}>鑽石的化學本質</h3>
              <p className="text-foreground/85 leading-[2] text-sm md:text-base" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
                鑽石是碳元素在極高壓力與溫度下形成的結晶體，每個碳原子以sp3混成軌域與周圍四個碳原子形成共價鍵，構成面心立方晶格（FCC）。這種緊密的三維共價鍵網絡賦予鑽石極高的硬度（莫氏10）、極低的壓縮性，以及特殊的光學性質——高折射率（2.417）使光線在鑽石內部產生全反射，形成肉眼可見的耀眼光彩。
              </p>

              <h3 className="text-base font-semibold text-foreground mt-8" style={{ fontFamily: "'Noto Serif TC', serif" }}>為何DNA可以成為碳源？</h3>
              <p className="text-foreground/85 leading-[2] text-sm md:text-base" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
                DNA（去氧核糖核酸）分子由四種核苷酸（腺嘌呤A、鳥嘌呤G、胸腺嘧啶T、胞嘧啶C）通過磷酸二酯鍵連接而成。這四種核苷酸均為有機分子，其化學式顯示碳元素佔其組成的相當比例——例如腺嘌呤的化學式為C₅H₅N₅，胸腺嘧啶為C₅H₆N₂O₂。將DNA高溫灰化後，碳元素可與其他元素分離，經純化後作為鑽石培育的原料。
              </p>

              {/* 技術比較表 */}
              <div className="mt-8">
                <h3 className="text-base font-semibold text-foreground mb-5" style={{ fontFamily: "'Noto Serif TC', serif" }}>兩種主要培育技術比較</h3>
                <div className="grid md:grid-cols-2 gap-5">
                  {[
                    {
                      method: "HPHT",
                      full: "高壓高溫法",
                      en: "High Pressure High Temperature",
                      params: [
                        { k: "壓力", v: "5–6 GPa（≈ 55,000大氣壓）" },
                        { k: "溫度", v: "1,400–1,600°C" },
                        { k: "培育時間", v: "6–12 週（依克拉數）" },
                        { k: "原理", v: "模擬地球地幔自然生成條件" },
                        { k: "適合生產", v: "彩色鑽石、近無色鑽石" },
                        { k: "晶體形態", v: "八面體或立方八面體" },
                      ],
                    },
                    {
                      method: "CVD",
                      full: "化學氣相沉積法",
                      en: "Chemical Vapor Deposition",
                      params: [
                        { k: "壓力", v: "低壓（0.1–1 Torr）" },
                        { k: "溫度", v: "700–900°C" },
                        { k: "培育時間", v: "4–10 週（依克拉數）" },
                        { k: "原理", v: "碳氣體電漿沉積於種晶表面" },
                        { k: "適合生產", v: "高純度無色鑽石（D–F色）" },
                        { k: "晶體形態", v: "層狀平板晶體" },
                      ],
                    },
                  ].map((tech) => (
                    <div key={tech.method} className="border border-border rounded-sm overflow-hidden">
                      <div className="bg-secondary px-5 py-4 border-b border-border">
                        <p className="text-xs text-muted-foreground mb-0.5" style={{ fontFamily: "'DM Mono', monospace" }}>{tech.method}</p>
                        <p className="text-sm font-semibold text-foreground" style={{ fontFamily: "'Noto Serif TC', serif" }}>{tech.full}</p>
                        <p className="text-xs text-muted-foreground mt-0.5" style={{ fontFamily: "'DM Mono', monospace" }}>{tech.en}</p>
                      </div>
                      <div className="divide-y divide-border">
                        {tech.params.map((p) => (
                          <div key={p.k} className="flex gap-4 px-5 py-3">
                            <span className="text-xs text-muted-foreground w-20 shrink-0 pt-0.5" style={{ fontFamily: "'DM Mono', monospace" }}>{p.k}</span>
                            <span className="text-xs text-foreground leading-relaxed" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>{p.v}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* 3. 製作流程 */}
          <section id="process">
            <SectionTitle en="Manufacturing Process" zh="製作流程" />
            <p className="text-foreground/85 leading-[2] text-sm md:text-base mb-10" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
              從DNA樣本採集至成品鑽石交付，整個流程分為六個主要階段，全程約需4–6個月。以下依序說明各階段的具體內容、技術細節及注意事項。
            </p>
            <div className="space-y-0">
              {steps.map((step, i) => (
                <div key={step.num} className="relative grid grid-cols-[auto_1fr] gap-6 pb-12 last:pb-0">
                  {/* Connector line */}
                  {i < steps.length - 1 && (
                    <div className="absolute left-[15px] top-10 bottom-0 w-px bg-border" />
                  )}
                  {/* Step indicator */}
                  <div className="relative z-10 flex flex-col items-center gap-1 pt-0.5">
                    <div className="w-8 h-8 rounded-full bg-card border-2 border-accent flex items-center justify-center shrink-0">
                      <span className="text-xs font-medium text-accent" style={{ fontFamily: "'DM Mono', monospace" }}>{String(i + 1).padStart(2, "0")}</span>
                    </div>
                  </div>
                  {/* Content */}
                  <div>
                    <p className="text-xs text-muted-foreground mb-0.5" style={{ fontFamily: "'DM Mono', monospace" }}>{step.en}</p>
                    <h3 className="text-base font-semibold text-foreground mb-4" style={{ fontFamily: "'Noto Serif TC', serif" }}>
                      {step.num}　{step.title}
                    </h3>
                    <div className="space-y-3">
                      {step.content.map((para, j) => (
                        <p key={j} className="text-sm text-foreground/80 leading-[2]" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
                          {para}
                        </p>
                      ))}
                    </div>
                    {step.note && (
                      <div className="mt-4 flex gap-3 bg-muted/60 border border-border rounded-sm px-4 py-3">
                        <span className="text-accent shrink-0 mt-0.5">
                          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                            <circle cx="6.5" cy="6.5" r="6" stroke="currentColor" strokeWidth="1"/>
                            <path d="M6.5 5.5v4M6.5 3.5v1" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
                          </svg>
                        </span>
                        <p className="text-xs text-muted-foreground leading-[1.8]" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
                          {step.note}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* 4. 品質與鑑定 */}
          <section id="quality">
            <SectionTitle en="Quality & Certification" zh="品質與鑑定" />
            <div className="space-y-5">
              <h3 className="text-base font-semibold text-foreground" style={{ fontFamily: "'Noto Serif TC', serif" }}>4C 評級標準</h3>
              <p className="text-foreground/85 leading-[2] text-sm md:text-base" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
                DNA鑽石與天然鑽石採用完全相同的國際4C評級系統，由GIA（美國寶石學院）或IGI（國際寶石學院）等獨立機構進行評定。
              </p>
              <div className="grid sm:grid-cols-2 gap-4 mt-4">
                {[
                  {
                    c: "克拉重量 Carat",
                    body: "鑽石的重量單位，1克拉 = 0.2克。克拉數越大，稀有度越高，價格呈非線性增長。DNA鑽石可提供0.25–2.0克拉的選擇範圍，較大克拉數需更長的培育時間。",
                  },
                  {
                    c: "顏色 Colour",
                    body: "以D（完全無色）至Z（明顯黃色）分級。D–F為無色，G–J為近無色，K–M為微黃。CVD技術較易生產D–H色等級的高品質無色鑽石；HPHT在某些條件下可生產飽和彩色鑽石。",
                  },
                  {
                    c: "淨度 Clarity",
                    body: "評估鑽石內外部的瑕疵情況，由FL（無瑕）至I3（明顯內含物）分為11個等級。實驗室培育鑽石的淨度通常優於天然鑽石，多數成品可達VS1至SI1等級。",
                  },
                  {
                    c: "切割 Cut",
                    body: "評估刻面角度、對稱性與拋光品質，分為Excellent、Very Good、Good、Fair、Poor五個等級。切割品質直接決定鑽石的視覺亮度，優秀的切割可讓普通淨度的鑽石顯現出色的光彩。",
                  },
                ].map((item) => (
                  <div key={item.c} className="border border-border rounded-sm p-5">
                    <p className="text-xs font-medium text-accent mb-3" style={{ fontFamily: "'DM Mono', monospace" }}>{item.c}</p>
                    <p className="text-sm text-foreground/80 leading-[1.9]" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>{item.body}</p>
                  </div>
                ))}
              </div>

              <h3 className="text-base font-semibold text-foreground mt-8" style={{ fontFamily: "'Noto Serif TC', serif" }}>鑑定書說明</h3>
              <p className="text-foreground/85 leading-[2] text-sm md:text-base" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
                每顆DNA鑽石均附有GIA或IGI出具的正式鑑定書。鑑定書上會明確標注「Lab Grown」字樣及起源資訊，並以雷射將鑑定書號碼刻於鑽石腰部，肉眼不可見，需使用放大鏡確認。鑑定書是珠寶保險、海關申報及二手流通的必要憑證，請妥善保存。
              </p>
            </div>
          </section>

          {/* 5. 與天然鑽石比較 */}
          <section id="comparison">
            <SectionTitle en="Comparison" zh="與天然鑽石比較" />
            <p className="text-foreground/85 leading-[2] text-sm md:text-base mb-6" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
              以下表格從多個維度比較DNA鑽石、天然鑽石與常見仿鑽產品（以莫桑石為代表），協助您做出知情的選擇。
            </p>
            <div className="overflow-x-auto border border-border rounded-sm">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-secondary border-b border-border">
                    <th className="text-left px-5 py-4 font-medium text-muted-foreground text-xs w-36" style={{ fontFamily: "'DM Mono', monospace" }}>比較項目</th>
                    <th className="text-left px-5 py-4 font-semibold text-accent text-xs" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>DNA鑽石</th>
                    <th className="text-left px-5 py-4 font-medium text-foreground text-xs" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>天然鑽石</th>
                    <th className="text-left px-5 py-4 font-medium text-foreground text-xs" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>莫桑石（仿鑽）</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {[
                    ["化學成分", "純碳 (C)", "純碳 (C)", "碳化矽 (SiC)"],
                    ["鑽石測試儀", "通過（顯示為鑽石）", "通過", "部分通過，部分不通過"],
                    ["硬度（莫氏）", "10", "10", "9.25"],
                    ["折射率", "2.417", "2.417", "2.65–2.69"],
                    ["GIA / IGI 鑑定書", "是（Lab-Grown）", "是（Natural）", "否（非鑽石鑑定書）"],
                    ["個人化DNA連結", "是", "否", "否"],
                    ["環境衝擊", "低（實驗室製造）", "極高（需大量開採）", "低（實驗室製造）"],
                    ["道德採購疑慮", "無", "存在衝突鑽石風險", "無"],
                    ["相對價格（同克拉數）", "天然鑽石的 30–50%", "最高", "遠低於鑽石"],
                  ].map(([attr, dna, nat, mos], i) => (
                    <tr key={attr} className={i % 2 === 1 ? "bg-muted/20" : ""}>
                      <td className="px-5 py-3.5 text-muted-foreground text-xs" style={{ fontFamily: "'DM Mono', monospace" }}>{attr}</td>
                      <td className="px-5 py-3.5 text-foreground font-medium text-xs" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>{dna}</td>
                      <td className="px-5 py-3.5 text-foreground/70 text-xs" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>{nat}</td>
                      <td className="px-5 py-3.5 text-foreground/70 text-xs" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>{mos}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground mt-3" style={{ fontFamily: "'DM Mono', monospace" }}>
              * 價格比較為市場概估，實際價格依克拉數、色澤及淨度等級而異。
            </p>
          </section>

          {/* 6. 保養 */}
          <section id="care">
            <SectionTitle en="Care & Maintenance" zh="保養與注意事項" />
            <div className="space-y-5">
              <p className="text-foreground/85 leading-[2] text-sm md:text-base" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>
                DNA鑽石的保養方式與天然鑽石完全相同，硬度10莫氏使其幾乎不會被刮傷，但仍有若干注意事項需了解。
              </p>
              <div className="space-y-4">
                {[
                  {
                    title: "日常清潔",
                    body: "以溫水、中性洗碗精及軟毛牙刷輕刷清潔，再以清水沖淨並用軟布擦乾。避免使用磨砂清潔劑或硬刷，以免損傷鑲嵌的金屬部分。每3–6個月進行一次深層超音波清潔（可委託珠寶商進行）。",
                  },
                  {
                    title: "儲存方式",
                    body: "鑽石雖然極硬，但仍可能刮傷其他寶石甚至另一顆鑽石。建議將DNA鑽石珠寶單獨存放於附有軟質內裡的珠寶盒或絨布袋中，避免與其他珠寶混放。",
                  },
                  {
                    title: "日常配戴注意",
                    body: "進行劇烈運動、接觸強力化學品（漂白劑、強酸鹼）、游泳或從事園藝工作時，建議暫時摘除珠寶，以保護鑲嵌金屬的完整性。鑽石本身不受一般化學品影響，但鑲嵌材質（金、鉑金等）可能受腐蝕。",
                  },
                  {
                    title: "定期檢查",
                    body: "建議每年至少一次將珠寶送交信任的珠寶商進行專業檢查，確認鑲嵌爪位是否有磨損或鬆動，並進行必要的維護調整，防止鑽石在磨損的鑲嵌中脫落。",
                  },
                ].map((item) => (
                  <div key={item.title} className="grid grid-cols-[auto_1fr] gap-5 py-4 border-b border-border last:border-0">
                    <span className="text-xs text-accent pt-1 shrink-0 w-4" style={{ fontFamily: "'DM Mono', monospace" }}>—</span>
                    <div>
                      <p className="text-sm font-semibold text-foreground mb-1.5" style={{ fontFamily: "'Noto Serif TC', serif" }}>{item.title}</p>
                      <p className="text-sm text-foreground/75 leading-[1.95]" style={{ fontFamily: "'Noto Sans TC', sans-serif" }}>{item.body}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* 7. FAQ */}
          <section id="faq">
            <SectionTitle en="Frequently Asked Questions" zh="常見問題" />
            <div className="divide-y divide-border border-t border-border">
              {faqData.map((item) => (
                <FAQItem key={item.q} q={item.q} a={item.a} />
              ))}
            </div>
          </section>

          {/* Bottom note */}
          <div className="border-t border-border pt-10 pb-4">
            <p className="text-xs text-muted-foreground leading-relaxed" style={{ fontFamily: "'DM Mono', monospace" }}>
              本頁資訊僅供一般性參考，實際製程參數、時程及品質指標依個別訂單條件而定。如有具體問題，請洽我們的產品顧問。
              <br />最後更新：2024年12月　｜　版本：v2.1
            </p>
          </div>

        </main>
      </div>
    </div>
  );
}
