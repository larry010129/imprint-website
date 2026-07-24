import { useEffect, useMemo, useState } from "react";
import type { ColumnDef, PaginationState, SortingState } from "@tanstack/react-table";
import {
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";

import {
  DataGrid,
  DataGridColumnHeader,
  DataGridContainer,
  DataGridPagination,
  DataGridTable,
} from "@/components/ui/data-grid-table";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button-1";
import { DeleteConfirmDialog } from "@/components/ui/delete-confirm-dialog";

export type ContentTab = "banners" | "testimonials" | "faq";

export type ContentBannerRow = {
  id: string;
  title: string;
  eyebrow: string;
  sort_order: number;
  is_published: boolean;
  image_url?: string;
};

export type ContentTestimonialRow = {
  id: string;
  name: string;
  category: string;
  city: string;
  text: string;
  sort_order: number;
  is_published: boolean;
  image_url?: string;
};

export type ContentFaqRow = {
  id: string;
  category_title: string;
  question: string;
  show_in_teaser: boolean;
  is_published: boolean;
};

export type AdminContentTablesProps = {
  tab: ContentTab;
  banners: ContentBannerRow[];
  testimonials: ContentTestimonialRow[];
  faqItems: ContentFaqRow[];
  onAdd: () => void;
  onEdit: (id: string) => void;
  onAction: (id: string, action: "publish" | "unpublish" | "delete") => void;
  onReorder?: (id: string, direction: "up" | "down") => void;
  onRendered?: () => void;
};

function truncate(s: string, n: number) {
  const t = String(s || "");
  return t.length > n ? `${t.slice(0, n)}…` : t;
}

function StatusBadge({ published }: { published: boolean }) {
  return (
    <span
      className={
        published
          ? "inline-flex rounded-full bg-[#EAF7EF] px-2.5 py-0.5 text-[11.5px] font-semibold text-[#3E8E62]"
          : "inline-flex rounded-full bg-[#F3F0EC] px-2.5 py-0.5 text-[11.5px] font-semibold text-[#8A817B]"
      }
    >
      {published ? "已發布" : "未發布"}
    </span>
  );
}

function ActionButtons({
  id,
  published,
  onEdit,
  onAction,
}: {
  id: string;
  published: boolean;
  onEdit: (id: string) => void;
  onAction: (id: string, action: "publish" | "unpublish" | "delete") => void;
}) {
  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <>
      <div className="flex flex-wrap items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
        <Button
          size="sm"
          variant="outline"
          className="border-input bg-background shadow-none hover:bg-background hover:text-foreground hover:border-input"
          onClick={() => onEdit(id)}
        >
          編輯
        </Button>
        {published ? (
          <Button
            size="sm"
            variant="ghost"
            className="hover:bg-transparent hover:text-foreground"
            onClick={() => onAction(id, "unpublish")}
          >
            下架
          </Button>
        ) : (
          <Button
            size="sm"
            variant="ghost"
            className="hover:bg-transparent hover:text-foreground"
            onClick={() => onAction(id, "publish")}
          >
            發布
          </Button>
        )}
        <Button
          size="sm"
          variant="destructive"
          className="rounded-md bg-[#c0392b] text-white shadow-none hover:bg-[#c0392b] hover:text-white focus-visible:ring-0"
          onClick={() => setDeleteOpen(true)}
        >
          刪除
        </Button>
      </div>
      <DeleteConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onConfirm={() => onAction(id, "delete")}
      />
    </>
  );
}

function ContentDataGrid<T extends { id: string }>({
  data,
  columns,
  emptyMessage,
  onRendered,
}: {
  data: T[];
  columns: ColumnDef<T>[];
  emptyMessage: string;
  onRendered?: () => void;
}) {
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });
  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useReactTable({
    data,
    columns,
    state: { pagination, sorting },
    onPaginationChange: setPagination,
    onSortingChange: setSorting,
    getRowId: (row) => row.id,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  useEffect(() => {
    onRendered?.();
  }, [onRendered, data, columns]);

  return (
    <DataGrid
      table={table}
      recordCount={data.length}
      emptyMessage={emptyMessage}
      tableLayout={{ dense: true, headerBackground: true, rowBorder: true, width: "fixed" }}
      tableClassNames={{ bodyRow: "hover:bg-transparent" }}
    >
      <div className="w-full space-y-2.5">
        <DataGridContainer>
          <ScrollArea className="w-full">
            <DataGridTable />
            <ScrollBar orientation="horizontal" />
          </ScrollArea>
        </DataGridContainer>
        <DataGridPagination />
      </div>
    </DataGrid>
  );
}

export default function AdminContentTables({
  tab,
  banners,
  testimonials,
  faqItems,
  onAdd,
  onEdit,
  onAction,
  onReorder,
  onRendered,
}: AdminContentTablesProps) {
  const bannerColumns = useMemo<ColumnDef<ContentBannerRow>[]>(
    () => [
      {
        id: "image",
        header: "圖",
        size: 72,
        cell: ({ row }) =>
          row.original.image_url ? (
            <img
              src={row.original.image_url}
              alt=""
              className="h-9 w-14 rounded object-cover"
              loading="lazy"
            />
          ) : (
            "—"
          ),
        meta: { skeleton: <Skeleton className="h-9 w-14" /> },
      },
      {
        accessorKey: "title",
        header: ({ column }) => <DataGridColumnHeader column={column} title="標題" />,
        size: 180,
        meta: { headerTitle: "標題", skeleton: <Skeleton className="h-4 w-28" /> },
      },
      {
        accessorKey: "eyebrow",
        header: "眉題",
        size: 120,
        cell: ({ getValue }) => (
          <span className="text-muted-foreground">{String(getValue() || "—")}</span>
        ),
        meta: { skeleton: <Skeleton className="h-4 w-16" /> },
      },
      {
        accessorKey: "sort_order",
        header: ({ column }) => <DataGridColumnHeader column={column} title="排序" />,
        size: 70,
        meta: { headerTitle: "排序", skeleton: <Skeleton className="h-4 w-8" /> },
      },
      {
        accessorKey: "is_published",
        header: "狀態",
        size: 90,
        cell: ({ getValue }) => <StatusBadge published={!!getValue()} />,
        meta: { skeleton: <Skeleton className="h-5 w-14 rounded-full" /> },
      },
      {
        id: "actions",
        header: "操作",
        size: 220,
        cell: ({ row }) => (
          <ActionButtons
            id={row.original.id}
            published={row.original.is_published}
            onEdit={onEdit}
            onAction={onAction}
          />
        ),
        meta: { skeleton: <Skeleton className="h-7 w-32" /> },
      },
    ],
    [onAction, onEdit],
  );

  const testimonialColumns = useMemo<ColumnDef<ContentTestimonialRow>[]>(
    () => [
      {
        id: "image",
        header: "圖",
        size: 72,
        cell: ({ row }) =>
          row.original.image_url ? (
            <img
              src={row.original.image_url}
              alt=""
              className="h-9 w-14 rounded object-cover"
              loading="lazy"
            />
          ) : (
            "—"
          ),
        meta: { skeleton: <Skeleton className="h-9 w-14" /> },
      },
      {
        accessorKey: "name",
        header: ({ column }) => <DataGridColumnHeader column={column} title="姓名" />,
        size: 100,
        meta: { headerTitle: "姓名", skeleton: <Skeleton className="h-4 w-16" /> },
      },
      {
        accessorKey: "category",
        header: "分類",
        size: 100,
        cell: ({ getValue }) => String(getValue() || "—"),
        meta: { skeleton: <Skeleton className="h-4 w-14" /> },
      },
      {
        accessorKey: "city",
        header: "城市",
        size: 80,
        cell: ({ getValue }) => String(getValue() || "—"),
        meta: { skeleton: <Skeleton className="h-4 w-10" /> },
      },
      {
        accessorKey: "text",
        header: "內容",
        size: 200,
        cell: ({ row }) => (
          <button
            type="button"
            className="max-w-[11rem] truncate text-left text-xs text-muted-foreground underline-offset-2 hover:underline"
            title="點擊查看完整內容並編輯"
            onClick={(e) => {
              e.stopPropagation();
              onEdit(row.original.id);
            }}
          >
            {truncate(row.original.text, 20) || "—"}
            {String(row.original.text || "").length > 20 ? (
              <span className="ml-1 rounded-full bg-[#F3F0EC] px-1.5 py-0.5 text-[10px] font-semibold text-[#6B6459]">
                詳情
              </span>
            ) : null}
          </button>
        ),
        meta: { skeleton: <Skeleton className="h-4 w-36" /> },
      },
      {
        accessorKey: "sort_order",
        header: ({ column }) => <DataGridColumnHeader column={column} title="排序" />,
        size: 100,
        cell: ({ row }) => (
          <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
            <span className="min-w-[1.25rem] text-center text-xs tabular-nums">
              {row.original.sort_order + 1}
            </span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 w-7 px-0 shadow-none"
              aria-label="上移"
              onClick={() => onReorder?.(row.original.id, "up")}
            >
              ↑
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 w-7 px-0 shadow-none"
              aria-label="下移"
              onClick={() => onReorder?.(row.original.id, "down")}
            >
              ↓
            </Button>
          </div>
        ),
        meta: { headerTitle: "排序", skeleton: <Skeleton className="h-4 w-16" /> },
      },
      {
        accessorKey: "is_published",
        header: "狀態",
        size: 90,
        cell: ({ getValue }) => <StatusBadge published={!!getValue()} />,
        meta: { skeleton: <Skeleton className="h-5 w-14 rounded-full" /> },
      },
      {
        id: "actions",
        header: "操作",
        size: 220,
        cell: ({ row }) => (
          <ActionButtons
            id={row.original.id}
            published={row.original.is_published}
            onEdit={onEdit}
            onAction={onAction}
          />
        ),
        meta: { skeleton: <Skeleton className="h-7 w-32" /> },
      },
    ],
    [onAction, onEdit, onReorder],
  );

  const faqColumns = useMemo<ColumnDef<ContentFaqRow>[]>(
    () => [
      {
        accessorKey: "id",
        header: "ID",
        size: 100,
        cell: ({ getValue }) => (
          <code className="rounded bg-[#F3F0EC] px-2 py-0.5 font-mono text-xs tracking-wide">
            {String(getValue())}
          </code>
        ),
        meta: { skeleton: <Skeleton className="h-5 w-16" /> },
      },
      {
        accessorKey: "category_title",
        header: "分類",
        size: 120,
        meta: { skeleton: <Skeleton className="h-4 w-16" /> },
      },
      {
        accessorKey: "question",
        header: "問題",
        size: 220,
        cell: ({ row }) => (
          <button
            type="button"
            className="max-w-[12rem] truncate text-left text-xs text-muted-foreground underline-offset-2 hover:underline"
            title="點擊查看完整內容並編輯"
            onClick={(e) => {
              e.stopPropagation();
              onEdit(row.original.id);
            }}
          >
            {truncate(row.original.question, 18) || "—"}
            {String(row.original.question || "").length > 18 ? (
              <span className="ml-1 rounded-full bg-[#F3F0EC] px-1.5 py-0.5 text-[10px] font-semibold text-[#6B6459]">
                詳情
              </span>
            ) : null}
          </button>
        ),
        meta: { skeleton: <Skeleton className="h-4 w-40" /> },
      },
      {
        accessorKey: "show_in_teaser",
        header: "首頁精選",
        size: 90,
        cell: ({ getValue }) => (getValue() ? "是" : "—"),
        meta: { skeleton: <Skeleton className="h-4 w-8" /> },
      },
      {
        accessorKey: "is_published",
        header: "狀態",
        size: 90,
        cell: ({ getValue }) => <StatusBadge published={!!getValue()} />,
        meta: { skeleton: <Skeleton className="h-5 w-14 rounded-full" /> },
      },
      {
        id: "actions",
        header: "操作",
        size: 220,
        cell: ({ row }) => (
          <ActionButtons
            id={row.original.id}
            published={row.original.is_published}
            onEdit={onEdit}
            onAction={onAction}
          />
        ),
        meta: { skeleton: <Skeleton className="h-7 w-32" /> },
      },
    ],
    [onAction, onEdit],
  );

  const addLabel =
    tab === "banners" ? "+ 新增輪播" : tab === "testimonials" ? "+ 新增見證" : "+ 新增 FAQ";

  return (
    <div className="space-y-3">
      <div className="flex justify-start">
        <Button
          size="sm"
          variant="primary"
          className="rounded-full bg-[#2b2320] text-white shadow-none hover:bg-[#2b2320] hover:text-primary-foreground focus-visible:ring-0"
          onClick={onAdd}
        >
          {addLabel}
        </Button>
      </div>
      {tab === "banners" ? (
        <ContentDataGrid
          data={banners}
          columns={bannerColumns}
          emptyMessage="尚無輪播"
          onRendered={onRendered}
        />
      ) : tab === "testimonials" ? (
        <ContentDataGrid
          data={testimonials}
          columns={testimonialColumns}
          emptyMessage="尚無見證"
          onRendered={onRendered}
        />
      ) : (
        <ContentDataGrid
          data={faqItems}
          columns={faqColumns}
          emptyMessage="尚無 FAQ"
          onRendered={onRendered}
        />
      )}
    </div>
  );
}
