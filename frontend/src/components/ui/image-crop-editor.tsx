import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";

import { fitCropPercent, type CropPercent } from "@/lib/crop-image";
import { cn } from "@/lib/utils";

type Handle = "move" | "nw" | "ne" | "sw" | "se";

export type ImageCropEditorProps = {
  src: string;
  aspectRatio?: number;
  crop: CropPercent;
  onCropChange: (crop: CropPercent) => void;
  onCropInit?: (crop: CropPercent) => void;
  className?: string;
  disabled?: boolean;
};

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function moveCrop(crop: CropPercent, dx: number, dy: number): CropPercent {
  const x = clamp(crop.x + dx, 0, 100 - crop.width);
  const y = clamp(crop.y + dy, 0, 100 - crop.height);
  return { ...crop, x, y };
}

function resizeCrop(
  start: CropPercent,
  handle: Handle,
  dx: number,
  dy: number,
  aspectRatio: number | undefined,
  imageAspect: number,
): CropPercent {
  let { x, y, width, height } = start;

  if (handle === "se") {
    width = start.width + dx;
  } else if (handle === "sw") {
    x = start.x + dx;
    width = start.width - dx;
  } else if (handle === "ne") {
    y = start.y + dy;
    width = start.width + dx;
  } else if (handle === "nw") {
    x = start.x + dx;
    y = start.y + dy;
    width = start.width - dx;
  }

  width = clamp(width, 8, 100);

  if (aspectRatio && aspectRatio > 0) {
    height = (width / aspectRatio) * imageAspect;
    if (height > 100) {
      height = 100;
      width = (height * aspectRatio) / imageAspect;
    }
  } else if (handle === "se" || handle === "sw") {
    height = start.height + dy;
  } else {
    height = start.height - dy;
  }

  height = clamp(height, 8, 100);

  if (handle === "nw" || handle === "ne") {
    y = start.y + start.height - height;
  }
  if (handle === "nw" || handle === "sw") {
    x = start.x + start.width - width;
  }

  x = clamp(x, 0, 100 - width);
  y = clamp(y, 0, 100 - height);
  width = clamp(width, 8, 100 - x);
  height = clamp(height, 8, 100 - y);

  return { x, y, width, height };
}

export function ImageCropEditor({
  src,
  aspectRatio,
  crop,
  onCropChange,
  onCropInit,
  className,
  disabled = false,
}: ImageCropEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [imageAspect, setImageAspect] = useState(1);
  const dragRef = useRef<{
    handle: Handle;
    startX: number;
    startY: number;
    startCrop: CropPercent;
  } | null>(null);

  useEffect(() => {
    setImageAspect(1);
  }, [src]);

  const initCrop = useCallback(
    (nextAspect: number) => {
      const next = fitCropPercent(nextAspect, aspectRatio);
      onCropInit?.(next);
      if (!onCropInit) onCropChange(next);
    },
    [aspectRatio, onCropChange, onCropInit],
  );

  const handleImageLoad = useCallback(
    (event: React.SyntheticEvent<HTMLImageElement>) => {
      const img = event.currentTarget;
      const nextAspect = img.naturalWidth / img.naturalHeight || 1;
      setImageAspect(nextAspect);
      initCrop(nextAspect);
    },
    [initCrop],
  );

  const onPointerDown = useCallback(
    (handle: Handle) => (event: ReactPointerEvent) => {
      if (disabled) return;
      event.preventDefault();
      event.stopPropagation();
      (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
      dragRef.current = {
        handle,
        startX: event.clientX,
        startY: event.clientY,
        startCrop: { ...crop },
      };
    },
    [crop, disabled],
  );

  const onPointerMove = useCallback(
    (event: ReactPointerEvent) => {
      const drag = dragRef.current;
      const container = containerRef.current;
      if (!drag || !container) return;

      const rect = container.getBoundingClientRect();
      const dx = ((event.clientX - drag.startX) / rect.width) * 100;
      const dy = ((event.clientY - drag.startY) / rect.height) * 100;

      if (drag.handle === "move") {
        onCropChange(moveCrop(drag.startCrop, dx, dy));
        return;
      }

      onCropChange(
        resizeCrop(
          drag.startCrop,
          drag.handle,
          dx,
          dy,
          aspectRatio,
          imageAspect,
        ),
      );
    },
    [aspectRatio, imageAspect, onCropChange],
  );

  const onPointerUp = useCallback((event: ReactPointerEvent) => {
    dragRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }, []);

  const handleClass =
    "absolute size-2.5 rounded-sm border border-white bg-[#2b2320] shadow-sm";

  return (
    <div className={cn("space-y-2", className)}>
      <p className="text-xs text-[#8a817b]">拖曳選取裁切範圍 · 拖動框線調整大小</p>
      <div
        ref={containerRef}
        className={cn(
          "relative select-none overflow-hidden rounded-lg border border-[#ede7e0] bg-[#fafaf8]",
          disabled && "pointer-events-none opacity-70",
        )}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <img
          key={src}
          src={src}
          alt=""
          className="block h-auto max-h-64 w-full"
          draggable={false}
          onLoad={handleImageLoad}
        />
        <div
          className="absolute cursor-move border-2 border-[#5ecfcf]"
          style={{
            left: `${crop.x}%`,
            top: `${crop.y}%`,
            width: `${crop.width}%`,
            height: `${crop.height}%`,
            boxShadow: "0 0 0 9999px rgba(43, 35, 32, 0.55)",
          }}
          onPointerDown={onPointerDown("move")}
        >
          <span
            className={cn(handleClass, "-left-1.5 -top-1.5 cursor-nwse-resize")}
            onPointerDown={onPointerDown("nw")}
          />
          <span
            className={cn(handleClass, "-right-1.5 -top-1.5 cursor-nesw-resize")}
            onPointerDown={onPointerDown("ne")}
          />
          <span
            className={cn(handleClass, "-bottom-1.5 -left-1.5 cursor-nesw-resize")}
            onPointerDown={onPointerDown("sw")}
          />
          <span
            className={cn(handleClass, "-bottom-1.5 -right-1.5 cursor-nwse-resize")}
            onPointerDown={onPointerDown("se")}
          />
        </div>
      </div>
    </div>
  );
}

export { fitCropPercent, type CropPercent };
