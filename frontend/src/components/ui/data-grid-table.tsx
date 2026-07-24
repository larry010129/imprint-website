import * as React from "react";
import {
  createContext,
  Fragment,
  useContext,
  type CSSProperties,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import {
  flexRender,
  type Cell,
  type Column,
  type ColumnFiltersState,
  type Header,
  type HeaderGroup,
  type Row,
  type RowData,
  type SortingState,
  type Table,
} from "@tanstack/react-table";
import { cva } from "class-variance-authority";
import {
  ArrowDown,
  ArrowUp,
  Check,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronsUpDown,
  CirclePlus,
  Settings2,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge-2";
import { Button } from "@/components/ui/button-1";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuPortal,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

declare module "@tanstack/react-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData extends RowData, TValue> {
    headerTitle?: string;
    headerClassName?: string;
    cellClassName?: string;
    skeleton?: ReactNode;
    expandedContent?: (row: TData) => ReactNode;
  }
}

export type DataGridApiFetchParams = {
  pageIndex: number;
  pageSize: number;
  sorting?: SortingState;
  filters?: ColumnFiltersState;
  searchQuery?: string;
};

export type DataGridApiResponse<T> = {
  data: T[];
  empty: boolean;
  pagination: { total: number; page: number };
};

export interface DataGridContextProps<TData extends object> {
  props: DataGridProps<TData>;
  table: Table<TData>;
  recordCount: number;
  isLoading: boolean;
}

export interface DataGridProps<TData extends object> {
  className?: string;
  table?: Table<TData>;
  recordCount: number;
  children?: ReactNode;
  onRowClick?: (row: TData) => void;
  isLoading?: boolean;
  loadingMode?: "skeleton" | "spinner";
  loadingMessage?: ReactNode | string;
  emptyMessage?: ReactNode | string;
  tableLayout?: {
    dense?: boolean;
    cellBorder?: boolean;
    rowBorder?: boolean;
    rowRounded?: boolean;
    stripped?: boolean;
    headerBackground?: boolean;
    headerBorder?: boolean;
    headerSticky?: boolean;
    width?: "auto" | "fixed";
    columnsVisibility?: boolean;
    columnsResizable?: boolean;
    columnsPinnable?: boolean;
    columnsMovable?: boolean;
  };
  tableClassNames?: {
    base?: string;
    header?: string;
    headerRow?: string;
    headerSticky?: string;
    body?: string;
    bodyRow?: string;
    footer?: string;
    edgeCell?: string;
  };
}

// React context cannot retain a provider's generic row type for arbitrary
// descendants. Erase it once at this boundary instead of forcing incompatible
// Table<TData> → Table<object> assertions throughout the component tree.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const DataGridContext = createContext<DataGridContextProps<any> | undefined>(undefined);

function useDataGrid() {
  const context = useContext(DataGridContext);
  if (!context) throw new Error("useDataGrid must be used within a DataGridProvider");
  return context;
}

function DataGridProvider<TData extends object>({
  children,
  table,
  ...props
}: DataGridProps<TData> & { table: Table<TData> }) {
  return (
    <DataGridContext.Provider
      value={{
        props,
        table,
        recordCount: props.recordCount,
        isLoading: props.isLoading || false,
      }}
    >
      {children}
    </DataGridContext.Provider>
  );
}

function DataGrid<TData extends object>({
  children,
  table,
  ...props
}: DataGridProps<TData>) {
  const defaultProps: Partial<DataGridProps<TData>> = {
    loadingMode: "skeleton",
    tableLayout: {
      dense: false,
      cellBorder: false,
      rowBorder: true,
      rowRounded: false,
      stripped: false,
      headerSticky: false,
      headerBackground: true,
      headerBorder: true,
      width: "fixed",
      columnsVisibility: false,
      columnsResizable: false,
      columnsPinnable: false,
      columnsMovable: false,
    },
    tableClassNames: {
      base: "",
      header: "",
      headerRow: "",
      headerSticky: "sticky top-0 z-10 bg-background/90 backdrop-blur-xs",
      body: "",
      bodyRow: "",
      footer: "",
      edgeCell: "",
    },
  };

  const mergedProps: DataGridProps<TData> = {
    ...defaultProps,
    ...props,
    tableLayout: { ...defaultProps.tableLayout, ...(props.tableLayout || {}) },
    tableClassNames: {
      ...defaultProps.tableClassNames,
      ...(props.tableClassNames || {}),
    },
  };

  if (!table) throw new Error('DataGrid requires a "table" prop');

  return (
    <DataGridProvider table={table} {...mergedProps}>
      {children}
    </DataGridProvider>
  );
}

function DataGridContainer({
  children,
  className,
  border = true,
}: {
  children: ReactNode;
  className?: string;
  border?: boolean;
}) {
  return (
    <div
      data-slot="data-grid"
      className={cn("grid w-full", border && "rounded-lg border border-border", className)}
    >
      {children}
    </div>
  );
}

const headerCellSpacingVariants = cva("", {
  variants: { size: { dense: "px-2.5 h-8", default: "px-4" } },
  defaultVariants: { size: "default" },
});

const bodyCellSpacingVariants = cva("", {
  variants: { size: { dense: "px-2.5 py-2", default: "px-4 py-3" } },
  defaultVariants: { size: "default" },
});

function getPinningStyles<TData>(column: Column<TData>): CSSProperties {
  const isPinned = column.getIsPinned();
  return {
    left: isPinned === "left" ? `${column.getStart("left")}px` : undefined,
    right: isPinned === "right" ? `${column.getAfter("right")}px` : undefined,
    position: isPinned ? "sticky" : "relative",
    width: column.getSize(),
    zIndex: isPinned ? 1 : 0,
  };
}

function DataGridTableBase({ children }: { children: ReactNode }) {
  const { props } = useDataGrid();
  return (
    <table
      data-slot="data-grid-table"
      className={cn(
        "w-full caption-bottom border-separate border-spacing-0 text-left text-sm font-normal text-foreground align-middle",
        props.tableLayout?.width === "fixed" ? "table-fixed" : "table-auto",
        props.tableClassNames?.base,
      )}
    >
      {children}
    </table>
  );
}

function DataGridTableHead({ children }: { children: ReactNode }) {
  const { props } = useDataGrid();
  return (
    <thead
      className={cn(
        props.tableClassNames?.header,
        props.tableLayout?.headerSticky && props.tableClassNames?.headerSticky,
      )}
    >
      {children}
    </thead>
  );
}

function DataGridTableHeadRow<TData>({
  children,
  headerGroup,
}: {
  children: ReactNode;
  headerGroup: HeaderGroup<TData>;
}) {
  const { props } = useDataGrid();
  return (
    <tr
      key={headerGroup.id}
      className={cn(
        "bg-muted/40",
        props.tableLayout?.headerBorder && "[&>th]:border-b",
        props.tableLayout?.cellBorder && "[&_>:last-child]:border-e-0",
        props.tableLayout?.stripped && "bg-transparent",
        props.tableLayout?.headerBackground === false && "bg-transparent",
        props.tableClassNames?.headerRow,
      )}
    >
      {children}
    </tr>
  );
}

function DataGridTableHeadRowCell<TData>({
  children,
  header,
}: {
  children: ReactNode;
  header: Header<TData, unknown>;
}) {
  const { props } = useDataGrid();
  const { column } = header;
  const isPinned = column.getIsPinned();
  const isLastLeftPinned = isPinned === "left" && column.getIsLastColumn("left");
  const isFirstRightPinned =
    isPinned === "right" && column.getIsFirstColumn("right");
  const headerCellSpacing = headerCellSpacingVariants({
    size: props.tableLayout?.dense ? "dense" : "default",
  });

  return (
    <th
      key={header.id}
      style={{
        ...(props.tableLayout?.width === "fixed" && {
          width: `${header.getSize()}px`,
        }),
        ...(props.tableLayout?.columnsPinnable &&
          column.getCanPin() &&
          getPinningStyles(column)),
      }}
      data-pinned={isPinned || undefined}
      data-last-col={
        isLastLeftPinned ? "left" : isFirstRightPinned ? "right" : undefined
      }
      className={cn(
        "relative h-10 text-left align-middle font-normal text-accent-foreground [&:has([role=checkbox])]:pe-0",
        headerCellSpacing,
        props.tableLayout?.cellBorder && "border-e",
        props.tableLayout?.columnsResizable && column.getCanResize() && "truncate",
        header.column.columnDef.meta?.headerClassName,
        column.getIndex() === 0 ||
          column.getIndex() === header.headerGroup.headers.length - 1
          ? props.tableClassNames?.edgeCell
          : "",
      )}
    >
      {children}
    </th>
  );
}

function DataGridTableHeadRowCellResize<TData>({
  header,
}: {
  header: Header<TData, unknown>;
}) {
  const { column } = header;
  return (
    <div
      onDoubleClick={() => column.resetSize()}
      onMouseDown={header.getResizeHandler()}
      onTouchStart={header.getResizeHandler()}
      className="absolute top-0 z-10 flex h-full w-4 -end-2 cursor-col-resize touch-none justify-center select-none before:absolute before:inset-y-0 before:w-px before:-translate-x-px before:bg-border"
    />
  );
}

function DataGridTableRowSpacer() {
  return <tbody aria-hidden="true" className="h-2" />;
}

function DataGridTableBody({ children }: { children: ReactNode }) {
  const { props } = useDataGrid();
  return (
    <tbody
      className={cn(
        "[&_tr:last-child]:border-0",
        props.tableLayout?.rowRounded &&
          "[&_td:first-child]:rounded-s-lg [&_td:last-child]:rounded-e-lg",
        props.tableClassNames?.body,
      )}
    >
      {children}
    </tbody>
  );
}

function rowClassName(props: DataGridProps<object>, table: Table<object>) {
  return cn(
    "hover:bg-muted/40 data-[state=selected]:bg-muted/50",
    props.onRowClick && "cursor-pointer",
    !props.tableLayout?.stripped &&
      props.tableLayout?.rowBorder &&
      "border-b border-border [&:not(:last-child)>td]:border-b",
    props.tableLayout?.cellBorder && "[&_>:last-child]:border-e-0",
    props.tableLayout?.stripped &&
      "odd:bg-muted/90 odd:hover:bg-muted hover:bg-transparent",
    table.options.enableRowSelection && "[&_>:first-child]:relative",
    props.tableClassNames?.bodyRow,
  );
}

function DataGridTableBodyRowSkeleton({ children }: { children: ReactNode }) {
  const { table, props } = useDataGrid();
  return <tr className={rowClassName(props, table)}>{children}</tr>;
}

function DataGridTableBodyRowSkeletonCell<TData>({
  children,
  column,
}: {
  children: ReactNode;
  column: Column<TData>;
}) {
  const { props, table } = useDataGrid();
  const bodyCellSpacing = bodyCellSpacingVariants({
    size: props.tableLayout?.dense ? "dense" : "default",
  });
  return (
    <td
      className={cn(
        "align-middle",
        bodyCellSpacing,
        props.tableLayout?.cellBorder && "border-e",
        props.tableLayout?.columnsResizable && column.getCanResize() && "truncate",
        column.columnDef.meta?.cellClassName,
        column.getIndex() === 0 ||
          column.getIndex() === table.getVisibleFlatColumns().length - 1
          ? props.tableClassNames?.edgeCell
          : "",
      )}
    >
      {children}
    </td>
  );
}

function DataGridTableBodyRow<TData>({
  children,
  row,
}: {
  children: ReactNode;
  row: Row<TData>;
}) {
  const { props, table } = useDataGrid();
  return (
    <tr
      data-state={
        table.options.enableRowSelection && row.getIsSelected()
          ? "selected"
          : undefined
      }
      onClick={() => props.onRowClick?.(row.original as object)}
      className={rowClassName(props, table)}
    >
      {children}
    </tr>
  );
}

function DataGridTableBodyRowExpandded<TData>({ row }: { row: Row<TData> }) {
  const { props, table } = useDataGrid();
  return (
    <tr
      className={cn(
        props.tableLayout?.rowBorder && "[&:not(:last-child)>td]:border-b",
      )}
    >
      <td colSpan={row.getVisibleCells().length}>
        {table
          .getAllColumns()
          .find((column) => column.columnDef.meta?.expandedContent)
          ?.columnDef.meta?.expandedContent?.(row.original as object)}
      </td>
    </tr>
  );
}

function DataGridTableBodyRowCell<TData>({
  children,
  cell,
}: {
  children: ReactNode;
  cell: Cell<TData, unknown>;
}) {
  const { props } = useDataGrid();
  const { column, row } = cell;
  const isPinned = column.getIsPinned();
  const isLastLeftPinned = isPinned === "left" && column.getIsLastColumn("left");
  const isFirstRightPinned =
    isPinned === "right" && column.getIsFirstColumn("right");
  const bodyCellSpacing = bodyCellSpacingVariants({
    size: props.tableLayout?.dense ? "dense" : "default",
  });

  return (
    <td
      key={cell.id}
      style={{
        ...(props.tableLayout?.columnsPinnable &&
          column.getCanPin() &&
          getPinningStyles(column)),
      }}
      data-pinned={isPinned || undefined}
      data-last-col={
        isLastLeftPinned ? "left" : isFirstRightPinned ? "right" : undefined
      }
      className={cn(
        "align-middle",
        bodyCellSpacing,
        props.tableLayout?.cellBorder && "border-e",
        props.tableLayout?.columnsResizable && column.getCanResize() && "truncate",
        cell.column.columnDef.meta?.cellClassName,
        column.getIndex() === 0 ||
          column.getIndex() === row.getVisibleCells().length - 1
          ? props.tableClassNames?.edgeCell
          : "",
      )}
    >
      {children}
    </td>
  );
}

function DataGridTableEmpty() {
  const { table, props } = useDataGrid();
  return (
    <tr>
      <td
        colSpan={table.getAllColumns().length}
        className="py-6 text-center text-muted-foreground"
      >
        {props.emptyMessage || "尚無資料"}
      </td>
    </tr>
  );
}

function DataGridTableLoader() {
  const { props } = useDataGrid();
  return (
    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
      <div className="flex items-center gap-2 rounded-md border bg-card px-4 py-2 text-sm font-medium text-muted-foreground shadow-xs">
        {props.loadingMessage || "載入中…"}
      </div>
    </div>
  );
}

function DataGridTableRowSelect<TData>({
  row,
  size,
}: {
  row: Row<TData>;
  size?: "sm" | "md" | "lg";
}) {
  return (
    <>
      <div
        className={cn(
          "absolute top-0 bottom-0 start-0 hidden w-[2px] bg-primary",
          row.getIsSelected() && "block",
        )}
      />
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label="Select row"
        size={size ?? "sm"}
        className="align-[inherit]"
      />
    </>
  );
}

function DataGridTableRowSelectAll({ size }: { size?: "sm" | "md" | "lg" }) {
  const { table, recordCount, isLoading } = useDataGrid();
  return (
    <Checkbox
      checked={
        table.getIsAllPageRowsSelected() ||
        (table.getIsSomePageRowsSelected() && "indeterminate")
      }
      disabled={isLoading || recordCount === 0}
      onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
      aria-label="Select all"
      size={size}
      className="align-[inherit]"
    />
  );
}

function DataGridTable() {
  const { table, isLoading, props } = useDataGrid();
  const pagination = table.getState().pagination;

  return (
    <DataGridTableBase>
      <DataGridTableHead>
        {table.getHeaderGroups().map((headerGroup, index) => (
          <DataGridTableHeadRow headerGroup={headerGroup} key={index}>
            {headerGroup.headers.map((header, hIndex) => {
              const { column } = header;
              return (
                <DataGridTableHeadRowCell header={header} key={hIndex}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                  {props.tableLayout?.columnsResizable &&
                    column.getCanResize() && (
                      <DataGridTableHeadRowCellResize header={header} />
                    )}
                </DataGridTableHeadRowCell>
              );
            })}
          </DataGridTableHeadRow>
        ))}
      </DataGridTableHead>

      {(props.tableLayout?.stripped || !props.tableLayout?.rowBorder) && (
        <DataGridTableRowSpacer />
      )}

      <DataGridTableBody>
        {props.loadingMode === "skeleton" &&
        isLoading &&
        pagination?.pageSize ? (
          Array.from({ length: pagination.pageSize }).map((_, rowIndex) => (
            <DataGridTableBodyRowSkeleton key={rowIndex}>
              {table.getVisibleFlatColumns().map((column, colIndex) => (
                <DataGridTableBodyRowSkeletonCell column={column} key={colIndex}>
                  {column.columnDef.meta?.skeleton}
                </DataGridTableBodyRowSkeletonCell>
              ))}
            </DataGridTableBodyRowSkeleton>
          ))
        ) : table.getRowModel().rows.length ? (
          table.getRowModel().rows.map((row) => (
            <Fragment key={row.id}>
              <DataGridTableBodyRow row={row}>
                {row.getVisibleCells().map((cell, colIndex) => (
                  <DataGridTableBodyRowCell cell={cell} key={colIndex}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </DataGridTableBodyRowCell>
                ))}
              </DataGridTableBodyRow>
              {row.getIsExpanded() && (
                <DataGridTableBodyRowExpandded row={row} />
              )}
            </Fragment>
          ))
        ) : (
          <DataGridTableEmpty />
        )}
      </DataGridTableBody>
    </DataGridTableBase>
  );
}

export interface DataGridPaginationProps {
  sizes?: number[];
  sizesSkeleton?: ReactNode;
  moreLimit?: number;
  info?: string;
  infoSkeleton?: ReactNode;
  className?: string;
}

function DataGridPagination(props: DataGridPaginationProps) {
  const { table, recordCount, isLoading } = useDataGrid();
  const mergedProps: DataGridPaginationProps = {
    sizes: [5, 10, 25, 50, 100],
    sizesSkeleton: <Skeleton className="h-8 w-44" />,
    moreLimit: 5,
    info: "{from} - {to} / {count}",
    infoSkeleton: <Skeleton className="h-8 w-60" />,
    ...props,
  };

  const btnBaseClasses = "size-7 p-0 text-sm";
  const pageIndex = table.getState().pagination.pageIndex;
  const pageSize = table.getState().pagination.pageSize;
  const from = recordCount === 0 ? 0 : pageIndex * pageSize + 1;
  const to = Math.min((pageIndex + 1) * pageSize, recordCount);
  const pageCount = table.getPageCount();
  const paginationInfo = (mergedProps.info || "")
    .replace("{from}", String(from))
    .replace("{to}", String(to))
    .replace("{count}", String(recordCount));

  const limit = mergedProps.moreLimit || 5;
  const groupStart = Math.floor(pageIndex / limit) * limit;
  const groupEnd = Math.min(groupStart + limit, pageCount);

  return (
    <div
      data-slot="data-grid-pagination"
      className={cn(
        "flex grow flex-col flex-wrap items-center justify-between gap-2.5 py-2.5 sm:flex-row sm:py-0",
        mergedProps.className,
      )}
    >
      <div className="order-2 flex flex-wrap items-center space-x-2.5 pb-2.5 sm:order-1 sm:pb-0">
        {isLoading ? (
          mergedProps.sizesSkeleton
        ) : (
          <>
            <div className="text-sm text-muted-foreground">每頁列數</div>
            <Select
              value={`${pageSize}`}
              onValueChange={(value) => table.setPageSize(Number(value))}
            >
              <SelectTrigger className="w-fit" size="sm">
                <SelectValue placeholder={`${pageSize}`} />
              </SelectTrigger>
              <SelectContent side="top" className="min-w-[50px] border-border/50 bg-background/70 shadow-lg backdrop-blur-xl backdrop-saturate-150">
                {mergedProps.sizes?.map((size) => (
                  <SelectItem key={size} value={`${size}`}>
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
        )}
      </div>
      <div className="order-1 flex flex-col items-center justify-center gap-2.5 pt-2.5 sm:order-2 sm:flex-row sm:justify-end sm:pt-0">
        {isLoading ? (
          mergedProps.infoSkeleton
        ) : (
          <>
            <div className="order-2 text-sm text-nowrap text-muted-foreground sm:order-1">
              {paginationInfo}
            </div>
            {pageCount > 1 && (
              <div className="order-1 flex items-center space-x-1 sm:order-2">
                <Button
                  size="sm"
                  mode="icon"
                  variant="ghost"
                  className={btnBaseClasses}
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                >
                  <ChevronLeftIcon className="size-4" />
                </Button>
                {Array.from({ length: groupEnd - groupStart }).map((_, idx) => {
                  const i = groupStart + idx;
                  return (
                    <Button
                      key={i}
                      size="sm"
                      mode="icon"
                      variant="ghost"
                      className={cn(btnBaseClasses, "text-muted-foreground", {
                        "bg-accent text-accent-foreground": pageIndex === i,
                      })}
                      onClick={() => table.setPageIndex(i)}
                    >
                      {i + 1}
                    </Button>
                  );
                })}
                <Button
                  size="sm"
                  mode="icon"
                  variant="ghost"
                  className={btnBaseClasses}
                  onClick={() => table.nextPage()}
                  disabled={!table.getCanNextPage()}
                >
                  <ChevronRightIcon className="size-4" />
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export interface DataGridColumnHeaderProps<TData, TValue>
  extends HTMLAttributes<HTMLDivElement> {
  column: Column<TData, TValue>;
  title?: string;
  icon?: ReactNode;
  filter?: ReactNode;
  visibility?: boolean;
}

function DataGridColumnHeader<TData, TValue>({
  column,
  title = "",
  icon,
  className,
  filter,
  visibility = false,
}: DataGridColumnHeaderProps<TData, TValue>) {
  const { isLoading, table, props, recordCount } = useDataGrid();

  const headerLabel = (
    <div
      className={cn(
        "inline-flex h-full items-center gap-1.5 text-[0.8125rem] font-normal text-accent-foreground [&_svg]:size-3.5 [&_svg]:opacity-60",
        className,
      )}
    >
      {icon}
      {title}
    </div>
  );

  const headerButton = (
    <Button
      variant="ghost"
      className={cn(
        "-ms-2 h-7 rounded-md px-2 font-normal text-secondary-foreground hover:bg-secondary hover:text-foreground data-[state=open]:bg-secondary",
        className,
      )}
      disabled={isLoading || recordCount === 0}
      onClick={() => {
        const isSorted = column.getIsSorted();
        if (isSorted === "asc") column.toggleSorting(true);
        else if (isSorted === "desc") column.clearSorting();
        else column.toggleSorting(false);
      }}
    >
      {icon}
      {title}
      {column.getCanSort() &&
        (column.getIsSorted() === "desc" ? (
          <ArrowDown className="mt-px size-[0.7rem]!" />
        ) : column.getIsSorted() === "asc" ? (
          <ArrowUp className="mt-px size-[0.7rem]!" />
        ) : (
          <ChevronsUpDown className="mt-px size-[0.7rem]!" />
        ))}
    </Button>
  );

  if ((props.tableLayout?.columnsVisibility && visibility) || filter) {
    return (
      <div className="flex h-full items-center justify-between gap-1.5">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>{headerButton}</DropdownMenuTrigger>
          <DropdownMenuContent className="w-40" align="start">
            {filter && <DropdownMenuLabel>{filter}</DropdownMenuLabel>}
            {column.getCanSort() && (
              <>
                <DropdownMenuItem
                  onClick={() =>
                    column.getIsSorted() === "asc"
                      ? column.clearSorting()
                      : column.toggleSorting(false)
                  }
                >
                  <ArrowUp className="size-3.5!" />
                  <span className="grow">升冪</span>
                  {column.getIsSorted() === "asc" && (
                    <Check className="size-4 text-primary opacity-100!" />
                  )}
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() =>
                    column.getIsSorted() === "desc"
                      ? column.clearSorting()
                      : column.toggleSorting(true)
                  }
                >
                  <ArrowDown className="size-3.5!" />
                  <span className="grow">降冪</span>
                  {column.getIsSorted() === "desc" && (
                    <Check className="size-4 text-primary opacity-100!" />
                  )}
                </DropdownMenuItem>
              </>
            )}
            {props.tableLayout?.columnsVisibility && visibility && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger>
                    <Settings2 className="size-3.5!" />
                    <span>欄位</span>
                  </DropdownMenuSubTrigger>
                  <DropdownMenuPortal>
                    <DropdownMenuSubContent>
                      {table
                        .getAllColumns()
                        .filter(
                          (col) =>
                            typeof col.accessorFn !== "undefined" &&
                            col.getCanHide(),
                        )
                        .map((col) => (
                          <DropdownMenuCheckboxItem
                            key={col.id}
                            checked={col.getIsVisible()}
                            onSelect={(event) => event.preventDefault()}
                            onCheckedChange={(value) =>
                              col.toggleVisibility(!!value)
                            }
                          >
                            {col.columnDef.meta?.headerTitle || col.id}
                          </DropdownMenuCheckboxItem>
                        ))}
                    </DropdownMenuSubContent>
                  </DropdownMenuPortal>
                </DropdownMenuSub>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    );
  }

  if (
    column.getCanSort() ||
    (props.tableLayout?.columnsResizable && column.getCanResize())
  ) {
    return <div className="flex h-full items-center">{headerButton}</div>;
  }

  return headerLabel;
}

export interface DataGridColumnFilterProps<TData, TValue> {
  column?: Column<TData, TValue>;
  title?: string;
  options: {
    label: string;
    value: string;
    icon?: React.ComponentType<{ className?: string }>;
  }[];
}

function DataGridColumnFilter<TData, TValue>({
  column,
  title,
  options,
}: DataGridColumnFilterProps<TData, TValue>) {
  const facets = column?.getFacetedUniqueValues();
  const selectedValues = new Set(column?.getFilterValue() as string[]);

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm">
          <CirclePlus className="size-4" />
          {title}
          {selectedValues?.size > 0 && (
            <>
              <Separator orientation="vertical" className="mx-2 h-4" />
              <Badge
                variant="secondary"
                className="rounded-sm px-1 font-normal lg:hidden"
              >
                {selectedValues.size}
              </Badge>
            </>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0" align="start">
        <Command>
          <CommandInput placeholder={title} />
          <CommandList>
            <CommandEmpty>查無結果</CommandEmpty>
            <CommandGroup>
              {options.map((option) => {
                const isSelected = selectedValues.has(option.value);
                return (
                  <CommandItem
                    key={option.value}
                    onSelect={() => {
                      if (isSelected) selectedValues.delete(option.value);
                      else selectedValues.add(option.value);
                      const filterValues = Array.from(selectedValues);
                      column?.setFilterValue(
                        filterValues.length ? filterValues : undefined,
                      );
                    }}
                  >
                    <div
                      className={cn(
                        "me-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary",
                        isSelected
                          ? "bg-primary text-primary-foreground"
                          : "opacity-50 [&_svg]:invisible",
                      )}
                    >
                      <Check className="h-4 w-4" />
                    </div>
                    <span>{option.label}</span>
                    {facets?.get(option.value) != null && (
                      <span className="ms-auto flex h-4 w-4 items-center justify-center font-mono text-xs">
                        {facets.get(option.value)}
                      </span>
                    )}
                  </CommandItem>
                );
              })}
            </CommandGroup>
            {selectedValues.size > 0 && (
              <>
                <CommandSeparator />
                <CommandGroup>
                  <CommandItem
                    onSelect={() => column?.setFilterValue(undefined)}
                    className="justify-center text-center"
                  >
                    清除篩選
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

function DataGridColumnVisibility<TData>({
  table,
  trigger,
}: {
  table: Table<TData>;
  trigger: ReactNode;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{trigger}</DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[150px]">
        <DropdownMenuLabel className="font-medium">顯示欄位</DropdownMenuLabel>
        {table
          .getAllColumns()
          .filter(
            (column) =>
              typeof column.accessorFn !== "undefined" && column.getCanHide(),
          )
          .map((column) => (
            <DropdownMenuCheckboxItem
              key={column.id}
              className="capitalize"
              checked={column.getIsVisible()}
              onSelect={(event) => event.preventDefault()}
              onCheckedChange={(value) => column.toggleVisibility(!!value)}
            >
              {column.columnDef.meta?.headerTitle || column.id}
            </DropdownMenuCheckboxItem>
          ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export {
  DataGrid,
  DataGridProvider,
  useDataGrid,
  DataGridContainer,
  DataGridTable,
  DataGridTableBase,
  DataGridTableBody,
  DataGridTableBodyRow,
  DataGridTableBodyRowCell,
  DataGridTableBodyRowExpandded,
  DataGridTableBodyRowSkeleton,
  DataGridTableBodyRowSkeletonCell,
  DataGridTableEmpty,
  DataGridTableHead,
  DataGridTableHeadRow,
  DataGridTableHeadRowCell,
  DataGridTableHeadRowCellResize,
  DataGridTableLoader,
  DataGridTableRowSelect,
  DataGridTableRowSelectAll,
  DataGridTableRowSpacer,
  DataGridPagination,
  DataGridColumnHeader,
  DataGridColumnFilter,
  DataGridColumnVisibility,
};
