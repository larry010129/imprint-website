import * as React from "react";
import { CheckIcon, Sparkles, XIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  featureGroupsForTrack,
  plansForTrack,
  type CellValue,
  type MembershipTrack,
  type MembershipTierId,
} from "@/lib/membership-tiers";
import { cn } from "@/lib/utils";

type MembershipComparisonProps = {
  currentTierId: MembershipTierId;
  upgradeHint?: string | null;
  track?: MembershipTrack;
};

function ComparisonCell({ value }: { value: CellValue }) {
  if (typeof value === "boolean") {
    return value ? (
      <>
        <CheckIcon className="mx-auto mb-1 stroke-emerald-600" size={18} aria-hidden="true" />
        <span className="sr-only">包含</span>
      </>
    ) : (
      <>
        <XIcon className="mx-auto mb-1 stroke-red-600" size={18} aria-hidden="true" />
        <span className="sr-only">不包含</span>
      </>
    );
  }

  return <div className="text-xs text-muted-foreground leading-snug">{value}</div>;
}

export const MembershipComparison = React.memo(function MembershipComparison({
  currentTierId,
  upgradeHint,
  track = "member",
}: MembershipComparisonProps) {
  const plans = plansForTrack(track).map((plan) => ({
    ...plan,
    highlighted: plan.id === currentTierId,
  }));
  const groups = featureGroupsForTrack(track);
  const isPartner = track === "partner";

  let rowIndex = 0;

  return (
    <section className="w-full max-w-6xl mx-auto text-[#2b2320]" aria-label="各等級權益比較">
      <div className="mb-5 px-1">
        <Badge variant="outline" className="mb-3 border-[#dcf2f2] bg-[#f4fbfb] text-[#2b2320]">
          <Sparkles className="size-3.5" aria-hidden="true" />
          {isPartner ? "合作廠商制度" : "會員制度"}
        </Badge>
        <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">各等級權益比較</h2>
        <p className="mt-2 max-w-2xl text-sm text-[#8a817b]">
          {isPartner
            ? "依本月 or 本年合格訂單筆數升級（擇優）；合作銘鑽僅限邀請。月 or 年曆重計。"
            : "訂單筆數 or 消費金額 or 好友邀請可升級／維持；銘鑽卡僅限品牌邀請。"}
        </p>
        {upgradeHint ? (
          <p className="mt-2 text-sm font-medium text-[#5ecfcf]">{upgradeHint}</p>
        ) : null}
      </div>

      <Table className="min-w-[720px] border border-gray-200 rounded-lg overflow-hidden">
        <TableHeader className="border border-gray-200">
          <TableRow className="border border-gray-200 hover:bg-transparent">
            <TableHead className="w-40 sticky left-0 z-20 bg-white border-r border-gray-200">
              權益項目
            </TableHead>
            {plans.map((plan) => (
              <TableHead
                key={plan.id}
                className={cn(
                  "text-center text-xs align-bottom border-r border-gray-200 last:border-r-0",
                  plan.highlighted && "bg-muted/40",
                )}
              >
                <div className="flex flex-col items-center gap-1.5">
                  <div className="flex h-5 items-center justify-center">
                    {plan.highlighted ? (
                      <span className="rounded-full bg-[#2b2320] px-2 py-0.5 text-[10px] font-semibold tracking-wide text-white whitespace-nowrap">
                        目前等級
                      </span>
                    ) : null}
                  </div>
                  <div
                    className="h-1.5 w-10 rounded-full"
                    style={{ background: plan.accent.chip }}
                    aria-hidden="true"
                  />
                  <div className="font-semibold text-sm text-[#2b2320]">{plan.name}</div>
                  {isPartner ? (
                    <div className="text-[10px] font-medium text-muted-foreground">合作</div>
                  ) : null}
                </div>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>

        <TableBody className="border border-gray-200">
          <TableRow className="border-t border-gray-200 hover:bg-muted/20 bg-muted/10">
            <TableCell
              colSpan={6}
              className="font-semibold border-l-4 border-gray-200 text-xs tracking-wide uppercase"
            >
              等級條件
            </TableCell>
          </TableRow>

          <TableRow
            className={cn(
              "hover:bg-muted/20 *:border-r border-t border-gray-200",
              rowIndex++ % 2 === 0 && "bg-muted/10",
            )}
          >
            <TableCell className="font-semibold sticky left-0 z-10 bg-inherit border-l-4 border-gray-200">
              達成門檻
            </TableCell>
            {plans.map((plan) => (
              <TableCell
                key={`price-${plan.id}`}
                className={cn(
                  "text-center py-3 border border-gray-200 text-xs text-muted-foreground leading-snug",
                  plan.highlighted && "bg-muted/30",
                )}
              >
                {plan.price}
              </TableCell>
            ))}
          </TableRow>

          <TableRow
            className={cn(
              "hover:bg-muted/20 *:border-r border-t border-gray-200",
              rowIndex++ % 2 === 0 && "bg-muted/10",
            )}
          >
            <TableCell className="font-semibold sticky left-0 z-10 bg-inherit border-l-4 border-gray-200">
              {isPartner ? "計算週期" : "續卡"}
            </TableCell>
            {plans.map((plan) => (
              <TableCell
                key={`cadence-${plan.id}`}
                className={cn(
                  "text-center py-3 border border-gray-200 text-xs text-muted-foreground leading-snug",
                  plan.highlighted && "bg-muted/30",
                )}
              >
                {plan.cadence}
              </TableCell>
            ))}
          </TableRow>

          {groups.map((group) => (
            <React.Fragment key={group.section}>
              <TableRow className="border-t border-gray-200 hover:bg-muted/20 bg-muted/10">
                <TableCell
                  colSpan={6}
                  className="font-semibold border-l-4 border-gray-200 text-xs tracking-wide uppercase"
                >
                  {group.section}
                </TableCell>
              </TableRow>
              {group.features.map((feature) => {
                const stripe = rowIndex++ % 2 === 0;
                return (
                  <TableRow
                    key={`${group.section}-${feature.label}`}
                    className={cn(
                      "hover:bg-muted/20 *:border-r border-t border-gray-200",
                      stripe && "bg-muted/10",
                    )}
                  >
                    <TableCell className="font-semibold sticky left-0 z-10 bg-inherit border-l-4 border-gray-200">
                      {feature.label}
                    </TableCell>
                    {feature.values.map((value, i) => (
                      <TableCell
                        key={`${feature.label}-${plans[i]?.id || i}`}
                        className={cn(
                          "text-center py-3 border border-gray-200",
                          plans[i]?.highlighted && "bg-muted/30",
                        )}
                      >
                        <ComparisonCell value={value} />
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
    </section>
  );
});
