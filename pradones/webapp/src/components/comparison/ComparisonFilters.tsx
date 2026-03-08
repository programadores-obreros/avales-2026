import { cn } from "@/lib/cn";
import { COMPARISON_STATUS } from "@/types/comparison";
import type { ComparisonStatus, ComparisonSummary } from "@/types/comparison";

interface ComparisonFiltersProps {
  statusFilter: ComparisonStatus | "todas";
  onStatusChange: (s: ComparisonStatus | "todas") => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  summary: ComparisonSummary;
  filteredCount: number;
}

const TABS = [
  {
    value: "todas" as const,
    label: "Todas",
    shortLabel: "Todas",
    color: "bg-primary",
  },
  {
    value: COMPARISON_STATUS.MANTIENE,
    label: "Se mantienen",
    shortLabel: "Mant.",
    color: "bg-amber-500",
  },
  {
    value: COMPARISON_STATUS.NUEVA,
    label: "Nuevas",
    shortLabel: "Nuevas",
    color: "bg-success",
  },
  {
    value: COMPARISON_STATUS.ELIMINADA,
    label: "Eliminadas",
    shortLabel: "Elim.",
    color: "bg-danger",
  },
] as const;

function getCount(
  value: ComparisonStatus | "todas",
  summary: ComparisonSummary,
): number {
  switch (value) {
    case "todas":
      return summary.maintained + summary.new_2026 + summary.removed;
    case COMPARISON_STATUS.MANTIENE:
      return summary.maintained;
    case COMPARISON_STATUS.NUEVA:
      return summary.new_2026;
    case COMPARISON_STATUS.ELIMINADA:
      return summary.removed;
  }
}

export function ComparisonFilters({
  statusFilter,
  onStatusChange,
  searchQuery,
  onSearchChange,
  summary,
  filteredCount,
}: ComparisonFiltersProps) {
  return (
    <div className="flex flex-col gap-2 sm:gap-3">
      {/* Status tabs */}
      <div className="flex gap-1 sm:flex-wrap sm:gap-1.5">
        {TABS.map((tab) => {
          const active = statusFilter === tab.value;
          const count = getCount(tab.value, summary);
          return (
            <button
              key={tab.value}
              onClick={() => onStatusChange(tab.value)}
              className={cn(
                "flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium transition-colors sm:gap-1.5 sm:px-3 sm:py-1.5 sm:text-xs",
                active
                  ? `${tab.color} text-white`
                  : "bg-surface-lighter text-text-secondary hover:text-white",
              )}
            >
              <span className="sm:hidden">{tab.shortLabel}</span>
              <span className="hidden sm:inline">{tab.label}</span>
              <span
                className={cn(
                  "rounded-full px-1 py-0.5 text-[9px] sm:px-1.5 sm:text-[10px]",
                  active ? "bg-white/20" : "bg-surface-card",
                )}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Search input + result count */}
      <div className="relative">
        <svg
          className="absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-text-muted sm:left-3 sm:h-4 sm:w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={`Buscar en ${filteredCount} resultado${filteredCount !== 1 ? "s" : ""}...`}
          className="w-full rounded-lg border border-border bg-surface-light py-1.5 pr-4 pl-8 text-xs text-text-primary placeholder-text-muted outline-none transition-colors focus:border-primary-light sm:py-2 sm:pl-10 sm:text-sm"
        />
        {searchQuery && (
          <button
            onClick={() => onSearchChange("")}
            className="absolute top-1/2 right-3 -translate-y-1/2 text-text-muted hover:text-white"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
