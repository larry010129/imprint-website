import { createRoot, type Root } from "react-dom/client";
import AdminOrdersTable, { type AdminOrdersTableProps } from "@/components/admin/AdminOrdersTable";
import AdminProductsTable, { type AdminProductsTableProps } from "@/components/admin/AdminProductsTable";
import AdminContentTables, {
  type AdminContentTablesProps,
} from "@/components/admin/AdminContentTables";
import PageLinkSelect, {
  type PageLinkSelectProps,
} from "@/components/admin/PageLinkSelect";
import "./index.css";

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
      unmount: typeof unmount;
    };
  }
}

window.AdminTables = {
  renderOrdersTable,
  renderProductsTable,
  renderContentTables,
  renderPageLinkSelect,
  unmount,
};
