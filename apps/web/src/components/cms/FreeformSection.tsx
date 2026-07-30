import type { CmsFreeformBlock } from "@/lib/cms";

import { str, type SectionProps } from "./types";

function BlockInner({
  block,
  edit,
}: {
  block: CmsFreeformBlock;
  edit: boolean;
}) {
  if (block.kind === "heading") {
    return (
      <h2
        data-cms-editable="text"
        data-cms-prop="blocks"
        data-cms-block-id={block.id}
        data-cms-block-field="text"
      >
        {block.text || "標題"}
      </h2>
    );
  }
  if (block.kind === "text") {
    return (
      <p
        data-cms-editable="text"
        data-cms-prop="blocks"
        data-cms-block-id={block.id}
        data-cms-block-field="text"
      >
        {block.text || "文字"}
      </p>
    );
  }
  if (block.kind === "button") {
    return (
      <a
        className="cms-btn cms-btn--solid"
        href={block.href || "#"}
        data-cms-editable="button"
        data-cms-prop="blocks"
        data-cms-block-id={block.id}
        data-cms-block-field="text"
        data-cms-href-prop="href"
      >
        {block.text || "按鈕"}
      </a>
    );
  }
  if (block.image_url) {
    return (
      <img
        src={block.image_url}
        alt={block.image_alt || ""}
        loading="lazy"
        decoding="async"
        data-cms-editable="image_url"
        data-cms-prop="blocks"
        data-cms-block-id={block.id}
        data-cms-block-field="image_url"
      />
    );
  }
  if (edit) {
    return (
      <button
        type="button"
        className="cms-image-upload-placeholder cms-freeform__image-ph"
        data-cms-editable="image_url"
        data-cms-prop="blocks"
        data-cms-block-id={block.id}
        data-cms-block-field="image_url"
      >
        <span>上傳圖片</span>
        <small>點擊選擇</small>
      </button>
    );
  }
  return null;
}

function BlocksLayer({
  blocks,
  edit,
  layer,
}: {
  blocks: CmsFreeformBlock[];
  edit: boolean;
  layer: "desktop" | "mobile";
}) {
  return (
    <div
      className={`cms-freeform__layer cms-freeform__layer--${layer}`}
      data-cms-freeform-layer={layer}
      hidden={layer === "mobile" ? undefined : undefined}
    >
      {blocks.map((block) => (
        <div
          key={`${layer}-${block.id}`}
          className={`cms-freeform__block cms-freeform__block--${block.kind}`}
          data-cms-freeform-block={block.id}
          data-cms-block-kind={block.kind}
          data-cms-freeform-device={layer}
          style={{
            left: `${block.x}%`,
            top: `${block.y}%`,
            width: `${block.w}%`,
            minHeight: `${block.h}%`,
            zIndex: block.z,
          }}
        >
          {edit ? (
            <>
              <button
                type="button"
                className="cms-freeform__drag"
                data-cms-freeform-drag
                aria-label="拖曳元素"
                title="拖曳移動"
              />
              <button
                type="button"
                className="cms-freeform__resize"
                data-cms-freeform-resize
                aria-label="調整大小"
                title="拖曳縮放"
              />
            </>
          ) : null}
          <BlockInner block={block} edit={edit} />
        </div>
      ))}
    </div>
  );
}

export default function FreeformSection({ section, ctx }: SectionProps) {
  const props = section.props || {};
  const height = Number(props.height) || 480;
  const edit = Boolean(ctx.inline);
  const blocks = Array.isArray(props.blocks)
    ? (props.blocks as CmsFreeformBlock[])
    : [];
  const mobile = Array.isArray(props.blocks_mobile)
    ? (props.blocks_mobile as CmsFreeformBlock[])
    : [];
  const hasMobile = mobile.length > 0;

  return (
    <section
      className={`cms-section cms-freeform${hasMobile ? " cms-freeform--has-mobile" : ""}`}
      data-cms-reveal
      data-cms-section-id={section.id}
      data-cms-section-type="freeform"
      style={{ ["--cms-freeform-h" as string]: `${height}px` }}
      id={str(props, "anchor") !== "end" ? str(props, "anchor") : undefined}
    >
      <div className="cms-freeform__canvas" data-cms-freeform-canvas="1">
        <BlocksLayer blocks={blocks} edit={edit} layer="desktop" />
        {hasMobile ? (
          <BlocksLayer blocks={mobile} edit={edit} layer="mobile" />
        ) : null}
        {edit && !blocks.length && !mobile.length ? (
          <p className="cms-freeform__empty">從此區塊右側工具列新增可拖曳元素。</p>
        ) : null}
      </div>
    </section>
  );
}
