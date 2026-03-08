import type { ComparisonSummary } from "@/types/comparison";

interface ComparisonStatsCardsProps {
  summary: ComparisonSummary;
}

const stats = [
  { key: "total_2022", label: "2022", color: "text-text-secondary" },
  { key: "total_2026", label: "2026", color: "text-primary-light" },
  { key: "maintained", label: "Mantienen", color: "text-amber-400" },
  { key: "new_2026", label: "Nuevas", color: "text-success" },
  { key: "removed", label: "Eliminadas", color: "text-danger" },
] as const;

export function ComparisonStatsCards({ summary }: ComparisonStatsCardsProps) {
  return (
    <div className="grid grid-cols-5 gap-1 rounded-lg border border-border bg-surface-card/60 px-2 py-1.5 sm:flex sm:items-center sm:gap-1 sm:px-3 sm:py-2">
      {stats.map((stat, i) => (
        <div key={stat.key} className="flex items-center sm:contents">
          {i > 0 && (
            <div className="mx-2 hidden h-6 w-px bg-border sm:block" />
          )}
          <div className="w-full text-center">
            <div
              className={`text-sm font-bold sm:text-base ${stat.color}`}
            >
              {summary[stat.key]}
            </div>
            <div className="text-[9px] text-text-muted sm:text-[10px]">
              {stat.label}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
