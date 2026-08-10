import { useEffect, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import AdminOrdersTable, { type AdminOrdersTableProps } from "@/components/admin/AdminOrdersTable";
import AdminProductsTable, { type AdminProductsTableProps } from "@/components/admin/AdminProductsTable";
import AdminContentTables, {
  type AdminContentTablesProps,
} from "@/components/admin/AdminContentTables";
import PageLinkSelect, {
  type PageLinkSelectProps,
} from "@/components/admin/PageLinkSelect";
import PageImageEditModal, {
  type PageImageEditModalProps,
} from "@/components/admin/PageImageEditModal";
import PageImageCreateModal, {
  type PageImageCreateModalProps,
} from "@/components/admin/PageImageCreateModal";
import BannerCropModal, {
  type BannerCropModalProps,
} from "@/components/admin/BannerCropModal";
import BannerImageUploadCards, {
  type BannerImageUploadCardsProps,
} from "@/components/admin/BannerImageUploadCards";
import ProductImageCropModal, {
  type ProductImageCropModalProps,
} from "@/components/admin/ProductImageCropModal";
import CmsPagesPanel, {
  type CmsPagesPanelProps,
} from "@/components/admin/CmsPagesPanel";
import AdminFeaturedVideoEditor, {
  type AdminFeaturedVideoEditorProps,
} from "@/components/admin/AdminFeaturedVideoEditor";
import ReleaseNotesEditor, {
  type ReleaseNotesEditorProps,
} from "@/components/admin/ReleaseNotesEditor";
import ReleaseNotesHistory, {
  type ReleaseNotesHistoryProps,
} from "@/components/admin/ReleaseNotesHistory";
import ReleaseNotesGate, {
  type ReleaseNotesGateProps,
} from "@/components/admin/ReleaseNotesGate";
import {
  ImageUploadField,
  type ImageUploadFieldProps,
} from "@/components/ui/image-upload";
import "./index.css";

/** Keeps `value` in sync after imperative onChange (DOM callers never re-render). */
function ImageUploadFieldBridge(props: ImageUploadFieldProps) {
  const [url, setUrl] = useState(props.value ?? "");
  useEffect(() => {
    setUrl(props.value ?? "");
  }, [props.value]);

  return (
    <ImageUploadField
      {...props}
      value={url}
      onChange={(next) => {
        setUrl(next);
        props.onChange?.(next);
      }}
    />
  );
}

const roots = new WeakMap<Element, Root>();

function getRoot(container: Element): Root {
  let root = roots.get(container);
  if (!root) {
    container.setAttribute("data-admin-root", "");
    root = createRoot(container);
    roots.set(container, root);
  }
  return root;
}

function renderOrdersTable(container: Element, props: AdminOrdersTableProps) {
  getRoot(container).render(<AdminOrdersTable {...props} />);
}

function renderProductsTable(container: Element, props: AdminProductsTableProps) {
  getRoot(container).render(<AdminProductsTable {...props} />);
}

function renderContentTables(container: Element, props: AdminContentTablesProps) {
  getRoot(container).render(<AdminContentTables {...props} />);
}

function renderPageLinkSelect(container: Element, props: PageLinkSelectProps) {
  getRoot(container).render(<PageLinkSelect {...props} />);
}

function renderPageImageEditModal(container: Element, props: PageImageEditModalProps) {
  getRoot(container).render(<PageImageEditModal {...props} />);
}

function renderPageImageCreateModal(container: Element, props: PageImageCreateModalProps) {
  getRoot(container).render(<PageImageCreateModal {...props} />);
}

function renderImageUploadField(container: Element, props: ImageUploadFieldProps) {
  getRoot(container).render(<ImageUploadFieldBridge {...props} />);
}

function renderBannerCropModal(container: Element, props: BannerCropModalProps) {
  getRoot(container).render(<BannerCropModal {...props} />);
}

function renderProductImageCropModal(
  container: Element,
  props: ProductImageCropModalProps,
) {
  getRoot(container).render(<ProductImageCropModal {...props} />);
}

function renderBannerImageUploadCards(container: Element, props: BannerImageUploadCardsProps) {
  getRoot(container).render(<BannerImageUploadCards {...props} />);
}

function renderCmsPagesPanel(container: Element, props: CmsPagesPanelProps) {
  getRoot(container).render(<CmsPagesPanel {...props} />);
}

function renderFeaturedVideoEditor(
  container: Element,
  props: AdminFeaturedVideoEditorProps,
) {
  getRoot(container).render(<AdminFeaturedVideoEditor {...props} />);
}

function renderReleaseNotesEditor(
  container: Element,
  props: ReleaseNotesEditorProps = {},
) {
  getRoot(container).render(<ReleaseNotesEditor {...props} />);
}

function renderReleaseNotesHistory(
  container: Element,
  props: ReleaseNotesHistoryProps = {},
) {
  getRoot(container).render(<ReleaseNotesHistory {...props} />);
}

function renderReleaseNotesGate(
  container: Element,
  props: ReleaseNotesGateProps = {},
) {
  getRoot(container).render(<ReleaseNotesGate {...props} />);
}

function bootReleaseNotesGate() {
  const credit = document.getElementById("adminReleaseNotesCredit");
  if (!credit) return;
  let mount = document.getElementById("adminReleaseNotesMount");
  if (!mount) {
    mount = document.createElement("div");
    mount.id = "adminReleaseNotesMount";
    document.body.appendChild(mount);
  }
  renderReleaseNotesGate(mount, { creditId: "adminReleaseNotesCredit" });
}

function unmount(container: Element) {
  const root = roots.get(container);
  if (root) {
    root.unmount();
    roots.delete(container);
  }
}

declare global {
  interface Window {
    AdminTables: {
      renderOrdersTable: typeof renderOrdersTable;
      renderProductsTable: typeof renderProductsTable;
      renderContentTables: typeof renderContentTables;
      renderPageLinkSelect: typeof renderPageLinkSelect;
      renderPageImageEditModal: typeof renderPageImageEditModal;
      renderPageImageCreateModal: typeof renderPageImageCreateModal;
      renderImageUploadField: typeof renderImageUploadField;
      renderBannerCropModal: typeof renderBannerCropModal;
      renderProductImageCropModal: typeof renderProductImageCropModal;
      renderBannerImageUploadCards: typeof renderBannerImageUploadCards;
      renderCmsPagesPanel: typeof renderCmsPagesPanel;
      renderFeaturedVideoEditor: typeof renderFeaturedVideoEditor;
      renderReleaseNotesEditor: typeof renderReleaseNotesEditor;
      renderReleaseNotesHistory: typeof renderReleaseNotesHistory;
      renderReleaseNotesGate: typeof renderReleaseNotesGate;
      unmount: typeof unmount;
    };
  }
}

window.AdminTables = {
  renderOrdersTable,
  renderProductsTable,
  renderContentTables,
  renderPageLinkSelect,
  renderPageImageEditModal,
  renderPageImageCreateModal,
  renderImageUploadField,
  renderBannerCropModal,
  renderProductImageCropModal,
  renderBannerImageUploadCards,
  renderCmsPagesPanel,
  renderFeaturedVideoEditor,
  renderReleaseNotesEditor,
  renderReleaseNotesHistory,
  renderReleaseNotesGate,
  unmount,
};

/** Auto-mount editor page and /admin credit gate. */
function bootReleaseNotesMounts() {
  const editorRoot = document.getElementById("admin-release-notes-root");
  if (editorRoot) {
    renderReleaseNotesEditor(editorRoot);
  }
  const historyRoot = document.getElementById("admin-release-notes-history-root");
  if (historyRoot) {
    renderReleaseNotesHistory(historyRoot);
  }
  // Prefer explicit mount; else attach when credit button exists.
  const gateRoot =
    document.getElementById("adminReleaseNotesMount") ||
    document.getElementById("admin-release-notes-gate-root");
  if (gateRoot) {
    renderReleaseNotesGate(gateRoot);
    return;
  }
  bootReleaseNotesGate();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootReleaseNotesMounts);
} else {
  bootReleaseNotesMounts();
}
