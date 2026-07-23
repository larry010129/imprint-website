import React, { useState } from "react";
import { cn } from "@/lib/utils";
import { Bookmark, Gem, Heart, MoreHorizontal } from "lucide-react";

export interface SocialCardProps {
  author?: {
    name?: string;
    username?: string;
    avatar?: string;
    /** Initial letter avatar — used when `avatar` URL is absent */
    initial?: string;
    timeAgo?: string;
  };
  content?: {
    text?: string;
    link?: {
      title?: string;
      description?: string;
      /** Product / link preview image (separate from author avatar) */
      imageUrl?: string;
      icon?: React.ReactNode;
    };
  };
  engagement?: {
    likes?: number;
    isLiked?: boolean;
    isBookmarked?: boolean;
  };
  /** compact ≈ 0.5× card for multi-column social grid */
  compact?: boolean;
  onLike?: () => void;
  onBookmark?: () => void;
  onMore?: () => void;
  className?: string;
}

export function SocialCard({
  author,
  content,
  engagement,
  compact = false,
  onLike,
  onBookmark,
  onMore,
  className,
}: SocialCardProps) {
  const [isLiked, setIsLiked] = useState(engagement?.isLiked ?? false);
  const [isBookmarked, setIsBookmarked] = useState(
    engagement?.isBookmarked ?? false,
  );
  const [likes, setLikes] = useState(engagement?.likes ?? 0);

  const handleLike = () => {
    setIsLiked(!isLiked);
    setLikes((prev) => (isLiked ? prev - 1 : prev + 1));
    onLike?.();
  };

  const handleBookmark = () => {
    setIsBookmarked(!isBookmarked);
    onBookmark?.();
  };

  return (
    <article
      className={cn(
        "w-full overflow-hidden border border-[#E3DCD3] bg-white shadow-[0_12px_40px_rgba(42,36,56,0.08)]",
        compact
          ? "rounded-2xl shadow-[0_6px_20px_rgba(42,36,56,0.07)]"
          : "mx-auto max-w-2xl rounded-3xl",
        className,
      )}
    >
      <div className="divide-y divide-[#E3DCD3]/80">
        <div className={compact ? "p-3" : "p-6"}>
          <div
            className={cn(
              "flex items-center justify-between",
              compact ? "mb-2.5" : "mb-4",
            )}
          >
            <div className={cn("flex items-center", compact ? "gap-2" : "gap-3")}>
              {author?.avatar ? (
                <img
                  src={author.avatar}
                  alt={author.name}
                  className={cn(
                    "rounded-full ring-2 ring-white",
                    compact ? "h-5 w-5" : "h-10 w-10",
                  )}
                />
              ) : author?.initial ? (
                <div
                  aria-hidden
                  className={cn(
                    "flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[#8eedf0] to-[#58cfd4] font-semibold text-[#2a1845] ring-2 ring-white",
                    compact ? "h-5 w-5 text-[9px]" : "h-10 w-10 text-sm",
                  )}
                  style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
                >
                  {author.initial}
                </div>
              ) : null}
              <div className="min-w-0">
                <h3
                  className={cn(
                    "truncate font-medium text-[#2a2438]",
                    compact ? "text-[11px]" : "text-sm",
                  )}
                  style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
                >
                  {author?.name}
                </h3>
                <p
                  className={cn(
                    "truncate text-[#8a817b]",
                    compact ? "text-[9px]" : "text-xs",
                  )}
                >
                  {author?.username ? `@${author.username}` : null}
                  {author?.username && author?.timeAgo ? " · " : null}
                  {author?.timeAgo}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onMore}
              className={cn(
                "rounded-full text-[#8a817b] transition-colors hover:bg-[#8eedf0]/20",
                compact ? "p-1" : "p-2",
              )}
              aria-label="更多"
            >
              <MoreHorizontal className={compact ? "h-3.5 w-3.5" : "h-5 w-5"} />
            </button>
          </div>

          <p
            className={cn(
              "text-[14px] leading-[1.75] text-[#2a2438]",
              compact ? "mb-2.5 line-clamp-4" : "mb-4",
            )}
          >
            {content?.text}
          </p>

          {content?.link ? (
            <div
              className={cn(
                "overflow-hidden rounded-xl border border-[#E3DCD3] bg-[#f7f4f1]",
                compact ? "mb-2.5" : "mb-4 rounded-2xl",
              )}
            >
              {content.link.imageUrl ? (
                <div className="aspect-[4/3] w-full overflow-hidden bg-[#8eedf0]/15">
                  <img
                    src={content.link.imageUrl}
                    alt=""
                    className="h-full w-full object-cover"
                    loading="lazy"
                    decoding="async"
                  />
                </div>
              ) : null}
              <div
                className={cn(
                  "flex items-center border-t border-[#E3DCD3]/80 bg-[#fdfcfa]",
                  compact ? "gap-1.5 px-2 py-1.5" : "gap-3 px-4 py-3",
                )}
              >
                <div
                  className={cn(
                    "flex shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-[#8eedf0] to-[#58cfd4] text-[#2a1845]",
                    compact ? "h-5 w-5 p-0" : "h-9 w-9 rounded-xl p-2",
                  )}
                >
                  {content.link.icon ?? (
                    <Gem className={compact ? "h-2.5 w-2.5" : "h-4 w-4"} aria-hidden />
                  )}
                </div>
                <div className="min-w-0">
                  <h4
                    className={cn(
                      "truncate font-medium text-[#2a2438]",
                      compact ? "text-[9px]" : "text-sm",
                    )}
                  >
                    {content.link.title}
                  </h4>
                  {content.link.description ? (
                    <p
                      className={cn(
                        "truncate text-[#8a817b]",
                        compact ? "text-[8px]" : "text-xs",
                      )}
                    >
                      {content.link.description}
                    </p>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}

          <div className={cn("flex items-center justify-between", compact ? "pt-1" : "pt-2")}>
            <button
              type="button"
              onClick={handleLike}
              className={cn(
                "flex items-center transition-colors",
                compact ? "gap-1 text-[9px]" : "gap-2 text-sm",
                isLiked ? "text-[#52c4c8]" : "text-[#8a817b] hover:text-[#52c4c8]",
              )}
            >
              <Heart
                className={cn(
                  "transition-all",
                  compact ? "h-3 w-3" : "h-5 w-5",
                  isLiked && "scale-110 fill-current",
                )}
              />
              <span>{likes}</span>
            </button>
            <button
              type="button"
              onClick={handleBookmark}
              className={cn(
                "rounded-full transition-all",
                compact ? "p-1" : "p-2",
                isBookmarked
                  ? "bg-[#8eedf0]/20 text-[#52c4c8]"
                  : "text-[#8a817b] hover:bg-[#8eedf0]/15",
              )}
              aria-label="收藏"
            >
              <Bookmark
                className={cn(
                  "transition-transform",
                  compact ? "h-3 w-3" : "h-5 w-5",
                  isBookmarked && "scale-110 fill-current",
                )}
              />
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}

export type TestimonialSocialCardProps = {
  name: string;
  role: string;
  category?: string;
  city?: string;
  text: string;
  image?: string;
  rating?: number;
  compact?: boolean;
  className?: string;
};

function testimonialLikeCount(seed: string, rating = 5): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = (Math.imul(31, h) + seed.charCodeAt(i)) >>> 0;
  }
  const base = 24 + rating * 8;
  const spread = 96 + rating * 12;
  return base + (h % spread);
}

export function TestimonialSocialCard({
  name,
  role,
  category,
  city,
  text,
  image,
  rating = 5,
  compact = false,
  className,
}: TestimonialSocialCardProps) {
  const safeName = String(name || "客戶").trim() || "客戶";
  const safeRole = String(role || "").trim();
  const safeText = String(text || "").trim();
  const slug = [category, city]
    .filter(Boolean)
    .join("_")
    .replace(/\s+/g, "")
    .replace(/・/g, "_");
  const likeSeed = [safeName, safeRole, category, city, safeText].filter(Boolean).join("|");

  return (
    <SocialCard
      compact={compact}
      className={className}
      author={{
        name: safeName,
        username: slug || safeRole.replace(/・/g, "_").replace(/\s+/g, ""),
        initial: safeName.charAt(0),
        timeAgo: safeRole,
      }}
      content={{
        text: safeText ? `「${safeText.replace(/^「|」$/g, "")}」` : "",
        link: image
          ? {
              title: category ? `${category} · 訂製款式` : "訂製款式",
              description: "銘印鑽石客戶訂製作品",
              imageUrl: image,
              icon: <Gem className={compact ? "h-2.5 w-2.5" : "h-4 w-4"} aria-hidden />,
            }
          : undefined,
      }}
      engagement={{
        likes: testimonialLikeCount(likeSeed, rating),
        isLiked: false,
        isBookmarked: false,
      }}
    />
  );
}
