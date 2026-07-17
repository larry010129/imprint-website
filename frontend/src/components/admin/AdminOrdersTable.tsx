import { Fragment, useEffect, useState } from "react";
import type { ColumnDef, PaginationState, SortingState } from "@tanstack/react-table";
import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
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

export interface OrderStatusOption {
  value: string;
  label: string;
}

export interface OrderTableRow {
  id: string;
  orderNumber: string;
  dateLabel: string;
  dateSort: string;
  customerName: string;
  categoryLabel: string;
  imageUrl: string;
  imageAlt: string;
  imageFallback: string;
  styleLabel: string;
  totalLabel: string;
  totalSort: number;
  status: string;
  statusLabel: string;
  isCancelled: boolean;
  statusOptions: OrderStatusOption[];
  detailId: string;
  detailHtml: string;
}

export interface AdminOrdersTableProps {
  rows: OrderTableRow[];
  pageSizeOptions?: number[];
  defaultPageSize?: number;
  onRendered?: () => void;
}

const columns: ColumnDef<OrderTableRow>[] = [
  {
    id: "select",
    header: () => (
      <label className="adx-check adx-check--head" title="全選">
        <input
          type="checkbox"
          className="adx-check-input"
          id="ordersSelectAll"
          aria-label="全選訂單"
        />
        <span className="adx-check-ui" aria-hidden="true"></span>
      </label>
    ),
    cell: ({ row }) => (
      <label className="adx-check">
        <input
          type="checkbox"
          className="adx-check-input order-row-check"
          data-order-id={row.original.id}
          disabled={row.original.isCancelled}
          aria-label="選取訂單"
        />
        <span className="adx-check-ui" aria-hidden="true"></span>
      </label>
    ),
    enableSorting: false,
    size: 40,
  },
  {
    id: "number",
    accessorFn: (r) => r.orderNumber,
    header: "編號",
  },
  {
    id: "created",
    accessorFn: (r) => r.dateSort,
    header: "日期",
    cell: ({ row }) => row.original.dateLabel,
  },
  {
    id: "customer",
    accessorFn: (r) => r.customerName,
    header: "客戶",
    cell: ({ row }) => <strong>{row.original.customerName}</strong>,
  },
  {
    id: "category",
    accessorFn: (r) => r.categoryLabel,
    header: "品項",
  },
  {
    id: "image",
    header: "商品圖",
    enableSorting: false,
    cell: ({ row }) =>
      row.original.imageUrl ? (
        <img
          className="order-style-thumb"
          src={row.original.imageUrl}
          alt={row.original.imageAlt}
          loading="lazy"
          data-fallback={row.original.imageFallback}
        />
      ) : (
        <span className="order-style-thumb--empty">—</span>
      ),
  },
  {
    id: "style",
    accessorFn: (r) => r.styleLabel,
    header: "款式",
  },
  {
    id: "total",
    accessorFn: (r) => r.totalSort,
    header: "含稅總計",
    cell: ({ row }) => row.original.totalLabel,
  },
  {
    id: "status",
    accessorFn: (r) => r.statusLabel,
    header: "狀態",
    cell: ({ row }) => (
      <span className={`order-status-badge order-status-badge--${row.original.status}`}>
        {row.original.statusLabel}
      </span>
    ),
  },
  {
    id: "actions",
    header: "操作",
    enableSorting: false,
    cell: ({ row }) => {
      const o = row.original;
      return (
        <div className="admin-actions-inner">
          {o.isCancelled ? (
            <span className="order-status-badge order-status-badge--cancelled">
              {o.statusLabel}
            </span>
          ) : (
            <select
              className="status-select"
              data-status={o.status}
              data-order-id={o.id}
              defaultValue={o.status}
            >
              {o.statusOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          )}
          {!o.isCancelled && (
            <button
              type="button"
              className="admin-delete-btn"
              data-cancel-order={o.id}
              title="取消訂單"
              aria-label="取消訂單"
            >
              ✕
            </button>
          )}
        </div>
      );
    },
  },
  {
    id: "detail",
    header: "詳情",
    enableSorting: false,
    cell: ({ row }) => (
      <button
        type="button"
        className="order-detail-btn"
        data-target={row.original.detailId}
        aria-expanded="false"
      >
        查看詳情
      </button>
    ),
  },
];

export default function AdminOrdersTable({
  rows,
  pageSizeOptions = [10, 20, 50, 100],
  defaultPageSize = 20,
  onRendered,
}: AdminOrdersTableProps) {
  const [sorting, setSorting] = useState<SortingState>([{ id: "created", desc: true }]);
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: defaultPageSize,
  });

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    getPaginationRowModel: getPaginationRowModel(),
    onPaginationChange: setPagination,
    state: { sorting, pagination },
  });

  const { pages, showLeftEllipsis, showRightEllipsis } = usePagination({
    currentPage: table.getState().pagination.pageIndex + 1,
    totalPages: Math.max(table.getPageCount(), 1),
    paginationItemsToDisplay: 5,
  });

  useEffect(() => {
    onRendered?.();
  });

  const visibleRows = table.getRowModel().rows;

  return (
    <div className="space-y-3">
      <Table className="admin-table records-table--compact">
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id} className="hover:bg-transparent">
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id} className="col-check-none">
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
              const o = row.original;
              return (
                <Fragment key={row.id}>
                  <TableRow
                    id={"admin-row-" + o.id}
                    className={cn("order-row-main", o.isCancelled && "is-cancelled")}
                    data-id={o.id}
                    data-status={o.status}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                  <tr className="order-detail-row" id={o.detailId} hidden>
                    <td colSpan={columns.length} dangerouslySetInnerHTML={{ __html: o.detailHtml }} />
                  </tr>
                </Fragment>
              );
            })
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="orders-empty">
                目前沒有訂單
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <div className="flex items-center justify-between gap-3 max-sm:flex-col">
        <p className="flex-1 whitespace-nowrap text-sm text-muted-foreground">
          第 <span className="text-foreground">{table.getState().pagination.pageIndex + 1}</span> 頁 / 共{" "}
          <span className="text-foreground">{Math.max(table.getPageCount(), 1)}</span> 頁 · 共{" "}
          {rows.length} 筆
        </p>

        <div className="grow">
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
                const isActive = page === table.getState().pagination.pageIndex + 1;
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
        </div>

        <div className="flex flex-1 justify-end">
          <select
            className="orders-bulk-select"
            value={table.getState().pagination.pageSize}
            aria-label="每頁筆數"
            onChange={(e) => table.setPageSize(Number(e.target.value))}
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size} / 頁
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
