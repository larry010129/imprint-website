import { useMemo } from "react";

export function usePagination({
  currentPage,
  totalPages,
  paginationItemsToDisplay = 5,
}: {
  currentPage: number;
  totalPages: number;
  paginationItemsToDisplay?: number;
}) {
  const { pages, showLeftEllipsis, showRightEllipsis } = useMemo(() => {
    const showLeftEllipsis = currentPage > paginationItemsToDisplay / 2 + 1;
    const showRightEllipsis =
      currentPage < totalPages - paginationItemsToDisplay / 2;

    let pages: number[] = [];

    if (totalPages <= paginationItemsToDisplay) {
      pages = Array.from({ length: totalPages }, (_, i) => i + 1);
    } else if (currentPage <= paginationItemsToDisplay - Math.floor(paginationItemsToDisplay / 2)) {
      pages = Array.from({ length: paginationItemsToDisplay - 1 }, (_, i) => i + 1);
    } else if (currentPage >= totalPages - Math.floor(paginationItemsToDisplay / 2)) {
      pages = Array.from(
        { length: paginationItemsToDisplay - 1 },
        (_, i) => totalPages - (paginationItemsToDisplay - 2) + i,
      );
    } else {
      const halfway = Math.ceil(paginationItemsToDisplay / 2);
      pages = Array.from(
        { length: paginationItemsToDisplay - 2 },
        (_, i) => currentPage - halfway + 2 + i,
      );
    }

    return { pages, showLeftEllipsis, showRightEllipsis };
  }, [currentPage, totalPages, paginationItemsToDisplay]);

  return { pages, showLeftEllipsis, showRightEllipsis };
}
