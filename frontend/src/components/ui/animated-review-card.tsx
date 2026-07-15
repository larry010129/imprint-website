import { useEffect, useState } from "react"
import { cva } from "class-variance-authority"
import { AnimatePresence, motion } from "motion/react"
import { Star } from "lucide-react"

import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { BorderBeam } from "@/components/ui/border-beam"

export interface Review {
  id: number | string
  name: string
  avatar?: string
  role?: string
  text: string
  rating: number
}

type ThemeColor = "default" | "primary" | "elegant" | "vibrant" | "minimal"

export interface AnimatedReviewCardsProps {
  reviews?: Review[]
  showAvatar?: boolean
  interactionType?: "drag" | "click"
  animationDuration?: number
  scaleStep?: number
  verticalSpacing?: number
  horizontalSpacing?: number
  maxStack?: number
  autoRotate?: boolean
  rotateInterval?: number
  theme?: ThemeColor
  showBorderBeam?: boolean
  classNames?: {
    container?: string
    card?: string
    cardContent?: string
    header?: string
    avatar?: string
    name?: string
    role?: string
    text?: string
    rating?: string
    star?: string
    activeStarColor?: string
    inactiveStarColor?: string
  }
}

const cardVariants = cva(
  "absolute h-[300px] w-[300px] overflow-hidden rounded-lg bg-background sm:w-[350px] md:h-[250px] md:w-[550px]",
  {
    variants: {
      theme: {
        default: "border border-border bg-background",
        primary: "bg-primary/10 border border-primary/20",
        elegant:
          "border border-zinc-200 bg-zinc-50 text-zinc-900 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100",
        vibrant:
          "border border-fuchsia-400 bg-gradient-to-br from-fuchsia-500 to-pink-500 text-white dark:border-fuchsia-700 dark:from-fuchsia-600 dark:to-pink-600",
        minimal:
          "border border-gray-100 bg-gray-50 text-gray-900 dark:border-gray-900 dark:bg-gray-950 dark:text-gray-100",
      },
      cursor: {
        drag: "cursor-grab active:cursor-grabbing",
        click: "cursor-pointer",
      },
    },
  },
)

const nameVariants = cva("text-lg font-semibold", {
  variants: {
    theme: {
      default: "text-foreground",
      primary: "text-primary",
      elegant: "text-zinc-900 dark:text-zinc-100",
      vibrant: "text-white",
      minimal: "text-gray-900 dark:text-gray-100",
    },
  },
})

const roleVariants = cva("mt-1 text-sm", {
  variants: {
    theme: {
      default: "text-muted-foreground",
      primary: "text-primary/70",
      elegant: "text-zinc-500 dark:text-zinc-400",
      vibrant: "text-white/80",
      minimal: "text-gray-500 dark:text-gray-400",
    },
  },
})

const textVariants = cva("select-none text-start text-sm leading-relaxed", {
  variants: {
    theme: {
      default: "text-foreground",
      primary: "text-primary/80",
      elegant: "text-zinc-600 dark:text-zinc-300",
      vibrant: "text-white/90",
      minimal: "text-gray-600 dark:text-gray-400",
    },
  },
})

const starColorVariants = {
  default: {
    active: "text-yellow-400 fill-current",
    inactive: "text-muted stroke-muted-foreground/20",
  },
  primary: {
    active: "text-primary",
    inactive: "text-primary/20",
  },
  elegant: {
    active: "text-zinc-700 dark:text-zinc-300 fill-current",
    inactive: "text-zinc-300 dark:text-zinc-600",
  },
  vibrant: {
    active: "text-white fill-current",
    inactive: "text-white/40",
  },
  minimal: {
    active: "text-gray-900 dark:text-gray-100 fill-current",
    inactive: "text-gray-200 dark:text-gray-700",
  },
}

function ReviewCardContent({
  review,
  theme,
  showAvatar,
  showBorderBeam,
  classNames,
}: {
  review: Review
  theme: ThemeColor
  showAvatar: boolean
  showBorderBeam: boolean
  classNames?: AnimatedReviewCardsProps["classNames"]
}) {
  const starColors = starColorVariants[theme]

  return (
    <div className={cn("relative h-full w-full rounded-lg p-6", classNames?.cardContent)}>
      <div className={cn("mb-4 flex items-center", classNames?.header)}>
        {showAvatar && review.avatar ? (
          <>
            <Avatar className={cn("mr-4 h-10 w-10 shrink-0", classNames?.avatar)}>
              <AvatarImage src={review.avatar} alt={review.name} />
              <AvatarFallback>{review.name.charAt(0)}</AvatarFallback>
            </Avatar>
            <h2 className={nameVariants({ theme, className: classNames?.name })}>
              {review.name}
            </h2>
          </>
        ) : (
          <div>
            <h2 className={nameVariants({ theme, className: classNames?.name })}>
              {review.name}
            </h2>
            {review.role && (
              <p className={roleVariants({ theme, className: classNames?.role })}>
                {review.role}
              </p>
            )}
          </div>
        )}
      </div>

      <p
        className={cn(
          textVariants({ theme, className: classNames?.text }),
          "max-h-[calc(100%-7.5rem)] overflow-y-auto pr-1",
        )}
      >
        {review.text}
      </p>

      <div className={cn("absolute bottom-6 left-6 flex items-center", classNames?.rating)}>
        {[...Array(5)].map((_, i) => (
          <Star
            key={i}
            className={cn(
              "h-5 w-5",
              i < review.rating
                ? classNames?.activeStarColor || starColors.active
                : classNames?.inactiveStarColor || starColors.inactive,
              classNames?.star,
            )}
          />
        ))}
      </div>

      {showBorderBeam && (
        <BorderBeam
          size={250}
          colorFrom={theme === "vibrant" ? "#ffffff" : "#5ecfcf"}
          colorTo={theme === "vibrant" ? "#ffffff" : "#9cefef"}
          duration={12}
          delay={9}
        />
      )}
    </div>
  )
}

export const AnimatedReviewCards = ({
  reviews: initialReviewsProp = [],
  showAvatar = false,
  interactionType = "drag",
  animationDuration = 0.3,
  scaleStep = 0.05,
  verticalSpacing = 10,
  horizontalSpacing = 20,
  maxStack = 4,
  autoRotate = true,
  rotateInterval = 6000,
  theme = "default",
  showBorderBeam = true,
  classNames,
}: AnimatedReviewCardsProps) => {
  const [reviews, setReviews] = useState(initialReviewsProp)
  const [isInteracting, setIsInteracting] = useState(false)

  useEffect(() => {
    setReviews(initialReviewsProp)
  }, [initialReviewsProp])

  const [isMobile, setIsMobile] = useState(false)
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return

    const mql = window.matchMedia("(max-width: 640px)")
    const update = () => setIsMobile(mql.matches)

    update()
    mql.addEventListener("change", update)
    return () => mql.removeEventListener("change", update)
  }, [])

  const handleInteraction = (index: number) => {
    setReviews((prevReviews) => {
      const newReviews = [...prevReviews]
      const [removed] = newReviews.splice(index, 1)
      newReviews.push(removed)
      return newReviews
    })
  }

  useEffect(() => {
    if (!autoRotate || isInteracting || reviews.length < 2) return
    const intervalId = setInterval(() => {
      handleInteraction(0)
    }, rotateInterval)
    return () => clearInterval(intervalId)
  }, [autoRotate, rotateInterval, isInteracting, reviews.length])

  if (reviews.length === 0) return null

  const visibleReviews = reviews.slice(0, Math.min(maxStack, reviews.length))

  return (
    <div
      className={cn(
        "not-prose relative flex h-[400px] w-full items-center justify-center md:h-[350px]",
        classNames?.container,
      )}
    >
      <AnimatePresence>
        {visibleReviews.map((review, index) => (
          <motion.div
            key={review.id}
            initial={{ scale: 0.8, y: 100, opacity: 0 }}
            animate={{
              scale: 1 + index * scaleStep,
              y: index * -verticalSpacing,
              x: !isMobile ? index * horizontalSpacing : undefined,
              opacity: index === visibleReviews.length - 1 ? 0.7 : 1,
              zIndex: visibleReviews.length - index,
            }}
            exit={{ scale: 0.8, y: 100, opacity: 0 }}
            transition={{ duration: animationDuration }}
            drag={interactionType === "drag" ? "y" : false}
            dragConstraints={interactionType === "drag" ? { top: 0, bottom: 0 } : undefined}
            onDragStart={() => setIsInteracting(true)}
            onDragEnd={() => {
              setIsInteracting(false)
              if (interactionType === "drag") handleInteraction(index)
            }}
            onClick={() => {
              if (interactionType === "click") {
                setIsInteracting(true)
                handleInteraction(index)
                setTimeout(() => setIsInteracting(false), 300)
              }
            }}
            title={interactionType === "drag" ? "向上拖曳切換" : "點擊切換"}
            className={cardVariants({
              theme,
              cursor: interactionType,
              className: classNames?.card,
            })}
          >
            <ReviewCardContent
              review={review}
              theme={theme}
              showAvatar={showAvatar}
              showBorderBeam={showBorderBeam && index === 0}
              classNames={classNames}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

export default AnimatedReviewCards
