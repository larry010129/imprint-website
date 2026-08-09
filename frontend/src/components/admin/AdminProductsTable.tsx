import { useEffect, useState } from "react";
import type { ColumnDef, PaginationState, SortingState } from "@tanstack/react-table";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp } from "lucide-react";

import { cn } from "@/lib/utils";
import { usePagination } from "@/components/hooks/use-pagination";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
} from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export interface ProductTableRow {
  id: string;
  category: string;
  categoryLabel: string;
  name: string;
  nameEn: string;
  thumbUrl: string;
  thumbFallback: string;
  statusLabel: string;
  statusClass: string;
  previewUrl: string;
  publishAction: "publish" | "unpublish";
  publishLabel: string;
  publishDisabled: boolean;
  publishDisabledReason: string;
  publishPrimary: boolean;
}

export interface AdminProductsTableProps {
  rows: ProductTableRow[];
  total?: number;
  pageIndex?: number;
  pageSize?: number;
  emptyLabel?: string;
  pageSizeOptions?: number[];
  defaultPageSize?: number;
  onPaginationChange?: (pagination: PaginationState) => void;
  onRendered?: () => void;
}

const columns: ColumnDef<ProductTableRow>[] = [
  {
    id: "drag",
    header: "",
    enableSorting: false,
    cell: () => (
      <button type="button" className="ap-drag-handle" aria-label="拖曳排序">
        ⋮⋮
      </button>
    ),
  },
  {
    id: "thumb",
    header: "縮圖",
    enableSorting: false,
    cell: ({ row }) =>
      row.original.thumbUrl ? (
        <img
          className="ap-thumb"
          src={row.original.thumbUrl}
          alt=""
          width={44}
          height={44}
          loading="lazy"
          decoding="async"
          fetchPriority="low"
          data-fallback={row.original.thumbFallback}
        />
      ) : (
        <span className="ap-thumb ap-thumb--empty">-</span>
      ),
  },
  {
    id: "category",
    accessorFn: (r) => r.categoryLabel,
    header: "品項",
  },
  {
    id: "name",
    accessorFn: (r) => r.name,
    header: "名稱",
    cell: ({ row }) => (
      <>
        <span className="name">{row.original.name}</span>
        {row.original.nameEn ? <span className="sub">{row.original.nameEn}</span> : null}
      </>
    ),
  },
  {
    id: "status",
    accessorFn: (r) => r.statusLabel,
    header: "狀態",
    cell: ({ row }) => (
      <span className={cn("ap-status-badge", row.original.statusClass)}>
        {row.original.statusLabel}
      </span>
    ),
  },
  {
    id: "actions",
    header: "操作",
    enableSorting: false,
    cell: ({ row }) => {
      const p = row.original;
      return (
        <div className="ap-actions">
          <button type="button" className="btn-sm ap-action" data-action="edit" data-id={p.id}>
            編輯
          </button>
          <a className="btn-sm ap-action" href={p.previewUrl} target="_blank" rel="noopener noreferrer">
            預覽
          </a>
          <button
            type="button"
            className={cn("btn-sm ap-action", p.publishPrimary && "btn-primary")}
            data-action={p.publishAction}
            data-id={p.id}
            disabled={p.publishDisabled}
            title={p.publishDisabled ? p.publishDisabledReason : undefined}
          >
            {p.publishLabel}
          </button>
          <button type="button" className="btn-sm ap-action" data-action="duplicate" data-id={p.id}>
            複製
          </button>
          <button
            type="button"
            className="btn-sm ap-action ap-action--danger"
            data-action="delete"
            data-id={p.id}
            data-name={p.name}
          >
            刪除
          </button>
        </div>
      );
    },
  },
];

export default function AdminProductsTable({
  rows,
  total,
  pageIndex: pageIndexProp,
  pageSize: pageSizeProp,
  emptyLabel = "此品項尚無商品。",
  pageSizeOptions = [5, 10, 25, 50],
  defaultPageSize = 10,
  onPaginationChange,
  onRendered,
}: AdminProductsTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: pageIndexProp ?? 0,
    pageSize: pageSizeProp ?? defaultPageSize,
  });

  useEffect(() => {
    setPagination((prev) => ({
      pageIndex: pageIndexProp ?? prev.pageIndex,
      pageSize: pageSizeProp ?? prev.pageSize,
    }));
  }, [pageIndexProp, pageSizeProp]);

  const recordCount = total ?? rows.length;
  const pageCount = Math.max(1, Math.ceil(recordCount / Math.max(pagination.pageSize, 1)));

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    manualPagination: true,
    pageCount,
    onPaginationChange: (updater) => {
      setPagination((prev) => {
        const next = typeof updater === "function" ? updater(prev) : updater;
        onPaginationChange?.(next);
        return next;
      });
    },
    state: { sorting, pagination },
    getRowId: (row) => row.id,
  });

  const pageIndex = table.getState().pagination.pageIndex;
  const pageSize = table.getState().pagination.pageSize;
  const from = recordCount === 0 ? 0 : pageIndex * pageSize + 1;
  const to = Math.min(pageIndex * pageSize + rows.length, recordCount);

  const { pages, showLeftEllipsis, showRightEllipsis } = usePagination({
    currentPage: pageIndex + 1,
    totalPages: pageCount,
    paginationItemsToDisplay: 5,
  });

  useEffect(() => {
    onRendered?.();
  }, [onRendered, rows]);

  const visibleRows = table.getRowModel().rows;

  return (
    <div className="space-y-2">
      <Table className="ap-table">
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id} className="hover:bg-transparent">
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder ? null : header.column.getCanSort() ? (
                    <div
                      className="flex cursor-pointer select-none items-center gap-1"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {{
                        asc: <ChevronUp className="shrink-0 opacity-60" size={14} aria-hidden="true" />,
                        desc: <ChevronDown className="shrink-0 opacity-60" size={14} aria-hidden="true" />,
                      }[header.column.getIsSorted() as string] ?? null}
                    </div>
                  ) : (
                    flexRender(header.column.columnDef.header, header.getContext())
                  )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {visibleRows.length ? (
            visibleRows.map((row) => {
              const p = row.original;
              return (
                <TableRow key={row.id} data-id={p.id} data-category={p.category} draggable="true">
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="ap-empty">
                {emptyLabel}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <div
        data-slot="products-table-pagination"
        className="flex items-center justify-between gap-3 max-sm:flex-col"
      >
        <div className="flex flex-1 flex-wrap items-center gap-2">
          <label className="whitespace-nowrap text-sm text-muted-foreground" htmlFor="ap-page-size">
            每頁顯示
          </label>
          <select
            id="ap-page-size"
            className="orders-bulk-select"
            value={pageSize}
            aria-label="每頁顯示筆數"
            onChange={(e) => table.setPageSize(Number(e.target.value))}
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </div>

        <div className="grow">
          {pageCount > 1 ? (
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <button
                    type="button"
                    className="admin-page-link"
                    onClick={() => table.previousPage()}
                    disabled={!table.getCanPreviousPage()}
                    aria-label="上一頁"
                  >
                    <ChevronLeft size={16} aria-hidden="true" />
                  </button>
                </PaginationItem>

                {showLeftEllipsis && (
                  <PaginationItem>
                    <PaginationEllipsis />
                  </PaginationItem>
                )}

                {pages.map((page) => {
                  const isActive = page === pageIndex + 1;
                  return (
                    <PaginationItem key={page}>
                      <button
                        type="button"
                        className={cn("admin-page-link", isActive && "is-current")}
                        onClick={() => table.setPageIndex(page - 1)}
                        aria-current={isActive ? "page" : undefined}
                      >
                        {page}
                      </button>
                    </PaginationItem>
                  );
                })}

                {showRightEllipsis && (
                  <PaginationItem>
                    <PaginationEllipsis />
                  </PaginationItem>
                )}

                <PaginationItem>
                  <button
                    type="button"
                    className="admin-page-link"
                    onClick={() => table.nextPage()}
                    disabled={!table.getCanNextPage()}
                    aria-label="下一頁"
                  >
                    <ChevronRight size={16} aria-hidden="true" />
                  </button>
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          ) : null}
        </div>

        <p className="flex flex-1 justify-end whitespace-nowrap text-sm text-muted-foreground max-sm:justify-center">
          第{" "}
          <span className="text-foreground">
            {from}–{to}
          </span>{" "}
          筆，共 <span className="text-foreground">{recordCount}</span> 筆
          {recordCount > 0 ? (
            <span className="ap-hint"> · 拖曳排序僅能調整本頁項目</span>
          ) : null}
        </p>
      </div>
    </div>
  );
}
