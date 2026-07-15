import { TestimonialsColumn } from "@/components/ui/testimonials-columns-1";
import type { Testimonial } from "@/components/ui/testimonials-columns-1";
import { motion } from "motion/react";

const testimonials: Testimonial[] = [
  {
    text: "牠陪了我十四年。現在牠變成一顆小小的、會發光的存在，還是天天跟著我出門。等待的三個月裡，我常常想像牠正在慢慢長成一顆星星。",
    image:
      "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=80&h=80&fit=crop",
    name: "沈小姐",
    role: "寵物鑽石・高雄（示意文案）",
  },
  {
    text: "猶豫了快兩年才決定。顧問從來沒有催促過我們，只是每次都把問題答得很清楚。拿到爸爸的鑽石那天，全家人都覺得——他一直都在。",
    image:
      "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=80&h=80&fit=crop",
    name: "林先生",
    role: "生命鑽石・台北（示意文案）",
  },
  {
    text: "用我們兩個人的頭髮，養出了一顆鑽石，鑲在她的婚戒上。交換戒指的時候，我跟她說：這顆鑽石裡，有你也有我。",
    image:
      "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=80&h=80&fit=crop",
    name: "張先生",
    role: "結髮鑽石・新竹（示意文案）",
  },
  {
    text: "寶寶滿月剃頭的時候，我把胎髮留了下來，沒想到真的可以做成鑽石。現在做成項鍊，等她長大，這會是我第一個要交給她的禮物。",
    image:
      "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=80&h=80&fit=crop",
    name: "周小姐",
    role: "滿月鑽石・台中（示意文案）",
  },
  {
    text: "把三個孩子的胎髮合在一起，做成一顆全家福鑽石。每次看著它，就像他們還在身邊吵吵鬧鬧，卻又安靜地陪著我。",
    image:
      "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=80&h=80&fit=crop",
    name: "吳太太",
    role: "全家福鑽石・台南（示意文案）",
  },
  {
    text: "媽媽離開後，我把她的髮絲做成鑽石鑲在胸針上。出席重要場合時戴上，總覺得她仍在為我加油。",
    image:
      "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=80&h=80&fit=crop",
    name: "陳小姐",
    role: "生命鑽石・桃園（示意文案）",
  },
  {
    text: "老狗離開那年冬天，我幾乎不敢再碰牠留下的項圈。後來把毛髮做成鑽石，終於能帶著牠去看我們常散步的海邊。",
    image:
      "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=80&h=80&fit=crop",
    name: "黃小姐",
    role: "寵物鑽石・花蓮（示意文案）",
  },
  {
    text: "結婚十週年，我們各自剪下一縷頭髮，一起養成這顆鑽石。它比任何珠寶店的成品都更像我們的故事。",
    image:
      "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=80&h=80&fit=crop",
    name: "劉先生",
    role: "結髮鑽石・台中（示意文案）",
  },
  {
    text: "祖母留給我的髮簪，我一直捨不得用。後來把髮絲做成鑽石傳給孫女，這是我能想到最溫柔的傳承。",
    image:
      "https://images.unsplash.com/photo-1519345182560-3f2917c472ef?w=80&h=80&fit=crop",
    name: "許先生",
    role: "傳家鑽石・台北（示意文案）",
  },
];

const firstColumn = testimonials.slice(0, 3);
const secondColumn = testimonials.slice(3, 6);
const thirdColumn = testimonials.slice(6, 9);

export default function StoriesTestimonials() {
  return (
    <section className="bg-background py-16 md:py-20 relative">
      <div className="container z-10 mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          viewport={{ once: true }}
          className="flex flex-col items-center justify-center max-w-[540px] mx-auto"
        >
          <div className="flex justify-center">
            <div className="border border-primary/30 py-1 px-4 rounded-lg text-sm tracking-widest text-primary">
              客戶見證
            </div>
          </div>

          <h2 className="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-bold tracking-tight mt-5 text-center">
            思念，在他們手中發著光
          </h2>
          <p className="text-center mt-5 opacity-75 leading-relaxed">
            每一顆銘印鑽石背後，都是一段真實的故事。
          </p>
          <p className="text-center mt-3 text-sm opacity-60 leading-relaxed">
            以下故事為示意文案，取得客戶同意後將替換為真實見證，化名亦可保留隱私。
          </p>
        </motion.div>

        <div className="flex justify-center gap-6 mt-10 [mask-image:linear-gradient(to_bottom,transparent,black_25%,black_75%,transparent)] max-h-[740px] overflow-hidden">
          <TestimonialsColumn testimonials={firstColumn} duration={15} />
          <TestimonialsColumn
            testimonials={secondColumn}
            className="stories-col-md"
            duration={19}
          />
          <TestimonialsColumn
            testimonials={thirdColumn}
            className="stories-col-lg"
            duration={17}
          />
        </div>
      </div>
    </section>
  );
}
