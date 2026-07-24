import * as React from "react";
import { ArrowRight, Check, Sparkles, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  MEMBERSHIP_FEATURE_GROUPS,
  MEMBERSHIP_PLANS,
  type CellValue,
  type MembershipTierId,
} from "@/lib/membership-tiers";
import { cn } from "@/lib/utils";

type MembershipComparisonProps = {
  currentTierId: MembershipTierId;
  upgradeHint?: string | null;
};

function ComparisonCell({
  value,
  highlighted,
}: {
  value: CellValue;
  highlighted: boolean;
}) {
  if (typeof value === "boolean") {
    return value ? (
      <span
        className={cn(
          "mx-auto flex size-5 items-center justify-center rounded-sm",
          highlighted ? "bg-[#2b2320]" : "bg-[#2b2320]/80",
        )}
      >
        <Check className="size-3.5 text-white" aria-hidden="true" />
        <span className="sr-only">包含</span>
      </span>
    ) : (
      <span className="mx-auto flex size-5 items-center justify-center rounded-sm bg-[#f7f4f1]">
        <X className="size-3.5 text-[#8a817b]" aria-hidden="true" />
        <span className="sr-only">不包含</span>
      </span>
    );
  }

  return (
    <span
      className={cn(
        "text-sm font-medium",
        highlighted ? "text-[#2b2320]" : "text-[#8a817b]",
      )}
    >
      {value}
    </span>
  );
}

const PLAN_CTAS: Record<MembershipTierId, { label: string; href: string }> = {
  standard: { label: "開始試算", href: "/shop/calculator.html" },
  companion: { label: "查看訂單", href: "/history.html" },
  legacy: { label: "聯絡顧問", href: "/contact.html" },
};

export const MembershipComparison = React.memo(function MembershipComparison({
  currentTierId,
  upgradeHint,
}: MembershipComparisonProps) {
  const plans = MEMBERSHIP_PLANS.map((plan) => ({
    ...plan,
    highlighted: plan.id === currentTierId,
  }));

  return (
    <section
      className="w-full rounded-3xl border border-[#ede7e0] bg-white px-4 py-8 text-[#2b2320] shadow-[0_12px_40px_rgba(43,35,32,0.06)] sm:px-6"
      aria-label="會員等級權益比較"
    >
      <div className="mb-6 max-w-2xl">
        <Badge variant="outline" className="mb-4 border-[#dcf2f2] bg-[#f4fbfb] text-[#2b2320]">
          <Sparkles className="size-3.5" aria-hidden="true" />
          會員制度
        </Badge>
        <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">各等級權益比較</h2>
        <p className="mt-3 text-sm text-[#8a817b]">
          依訂單累積自動升級。您目前的等級已標示，可對照各方案差異。
        </p>
        {upgradeHint ? (
          <p className="mt-2 text-sm font-medium text-[#5ecfcf]">{upgradeHint}</p>
        ) : null}
      </div>

      <div className="relative">
        <div className="overflow-x-auto rounded-xl border border-[#ede7e0]">
          <Table className="table-fixed text-sm">
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="sticky top-0 z-20 w-[34%] border-b border-[#ede7e0] bg-white align-bottom">
                  <span className="inline-block pb-3 text-xs font-semibold tracking-wide text-[#8a817b] uppercase">
                    權益項目
                  </span>
                </TableHead>
                {plans.map((plan) => (
                  <TableHead
                    key={plan.id}
                    className={cn(
                      "sticky top-0 z-20 border-b border-[#ede7e0] text-center align-bottom",
                      plan.highlighted ? "bg-[#f4fbfb]" : "bg-white",
                    )}
                  >
                    <div className="relative flex flex-col items-center gap-1 py-3">
                      {plan.highlighted ? (
                        <Badge className="absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 bg-[#5ecfcf] text-[#2b2320] hover:bg-[#5ecfcf]">
                          目前等級
                        </Badge>
                      ) : null}
                      <span className="text-sm font-semibold text-[#2b2320]">{plan.name}</span>
                      <span className="text-base font-bold text-[#2b2320]">{plan.price}</span>
                      <span className="text-xs font-normal text-[#8a817b]">{plan.cadence}</span>
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>

            <TableBody>
              {MEMBERSHIP_FEATURE_GROUPS.map((group) => (
                <React.Fragment key={group.section}>
                  <TableRow className="bg-[#fafaf8] hover:bg-[#fafaf8]">
                    <TableCell
                      colSpan={4}
                      className="py-2 text-xs font-semibold tracking-wide text-[#2b2320] uppercase"
                    >
                      {group.section}
                    </TableCell>
                  </TableRow>
                  {group.features.map((feature) => (
                    <TableRow key={`${group.section}-${feature.label}`}>
                      <TableCell className="py-2.5 font-medium text-[#2b2320]">
                        {feature.label}
                      </TableCell>
                      {feature.values.map((value, i) => (
                        <TableCell
                          key={`${feature.label}-${plans[i].id}`}
                          className={cn(
                            "py-2.5 text-center",
                            plans[i].highlighted && "bg-[#f4fbfb]/60",
                          )}
                        >
                          <ComparisonCell value={value} highlighted={plans[i].highlighted} />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </React.Fragment>
              ))}

              <TableRow className="hover:bg-transparent">
                <TableCell className="py-4" />
                {plans.map((plan) => {
                  const cta = PLAN_CTAS[plan.id];
                  return (
                    <TableCell
                      key={`cta-${plan.id}`}
                      className={cn("py-4 text-center", plan.highlighted && "bg-[#f4fbfb]/60")}
                    >
                      <Button
                        asChild
                        size="sm"
                        variant={plan.highlighted ? "default" : "secondary"}
                        className={cn(
                          "w-full rounded-full",
                          plan.highlighted && "bg-[#2b2320] hover:bg-[#2b2320]/90",
                        )}
                      >
                        <a href={cta.href}>
                          {plan.highlighted ? "您目前的等級" : cta.label}
                          <ArrowRight className="size-3.5" aria-hidden="true" />
                        </a>
                      </Button>
                    </TableCell>
                  );
                })}
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>
    </section>
  );
});
