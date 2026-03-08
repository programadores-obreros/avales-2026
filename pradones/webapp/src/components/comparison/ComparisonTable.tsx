import { useEffect, useRef } from "react";
import { cn } from "@/lib/cn";
import { COMPARISON_STATUS } from "@/types/comparison";
import type { ComparisonEntry } from "@/types/comparison";

interface ComparisonTableProps {
  entries: ComparisonEntry[];
  selectedEntry: ComparisonEntry | null;
  onEntryClick: (entry: ComparisonEntry) => void;
}

const STATUS_STYLES = {
  [COMPARISON_STATUS.MANTIENE]: {
    border: "border-l-amber-500",
    bg: "bg-amber-500/5",
    badge: "bg-amber-500/20 text-amber-400",
    label: "Se mantiene",
    shortLabel: "Mant.",
  },
  [COMPARISON_STATUS.NUEVA]: {
    border: "border-l-success",
    bg: "bg-success/5",
    badge: "bg-success/20 text-success",
    label: "Nueva",
    shortLabel: "Nueva",
  },
  [COMPARISON_STATUS.ELIMINADA]: {
    border: "border-l-danger",
    bg: "bg-danger/5",
    badge: "bg-danger/20 text-danger",
    label: "Eliminada",
    shortLabel: "Elim.",
  },
} as const;

export function ComparisonTable({
  entries,
  selectedEntry,
  onEntryClick,
}: ComparisonTableProps) {
  const rowRefs = useRef<Map<number, HTMLElement>>(new Map());

  useEffect(() => {
    if (selectedEntry) {
      const row = rowRefs.current.get(selectedEntry.id);
      if (row) {
        row.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [selectedEntry]);

  if (entries.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center py-12 text-sm text-text-muted">
        No se encontraron resultados
      </div>
    );
  }

  return (
    <>
      {/* Mobile: stacked cards */}
      <div className="flex flex-1 flex-col gap-1.5 overflow-auto sm:hidden">
        {entries.map((entry) => {
          const style = STATUS_STYLES[entry.estado];
          const isSelected = selectedEntry?.id === entry.id;
          const hasCoords = entry.lat !== null;

          return (
            <div
              key={entry.id}
              ref={(el) => {
                if (el) rowRefs.current.set(entry.id, el);
              }}
              onClick={() => onEntryClick(entry)}
              className={cn(
                "cursor-pointer rounded-lg border-l-3 px-3 py-2 transition-colors",
                style.border,
                isSelected
                  ? "bg-primary/15 ring-1 ring-primary-light ring-inset"
                  : "bg-surface-card/40 hover:bg-surface-lighter",
                !hasCoords && "opacity-60",
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-text-primary">
                    {entry.establecimiento}
                  </div>
                  <div className="mt-0.5 truncate text-[11px] text-text-muted">
                    {entry.direccion}
                  </div>
                </div>
                <span
                  className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-medium ${style.badge}`}
                >
                  {style.shortLabel}
                </span>
              </div>
              <div className="mt-1 flex items-center gap-3 text-[11px] text-text-secondary">
                <span>
                  M22: <span className="text-text-primary">{entry.mesa_2022 || "—"}</span>
                </span>
                <span className="text-text-muted">→</span>
                <span>
                  M26: <span className="text-text-primary">{entry.mesa_2026 || "—"}</span>
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Desktop: table */}
      <div className="hidden flex-1 overflow-auto rounded-lg border border-border sm:block">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 z-10 bg-surface-card text-xs text-text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">Estado</th>
              <th className="px-3 py-2 font-medium">Establecimiento</th>
              <th className="hidden px-3 py-2 font-medium md:table-cell">
                Dirección
              </th>
              <th className="px-3 py-2 font-medium">Mesa 22</th>
              <th className="px-3 py-2 font-medium">Mesa 26</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {entries.map((entry) => {
              const style = STATUS_STYLES[entry.estado];
              const isSelected = selectedEntry?.id === entry.id;
              const hasCoords = entry.lat !== null;

              return (
                <tr
                  key={entry.id}
                  ref={(el) => {
                    if (el) rowRefs.current.set(entry.id, el);
                  }}
                  onClick={() => onEntryClick(entry)}
                  className={cn(
                    "border-l-3 cursor-pointer transition-colors",
                    style.border,
                    isSelected
                      ? "bg-primary/15 ring-1 ring-primary-light ring-inset"
                      : `hover:${style.bg} hover:bg-surface-lighter`,
                    !hasCoords && "opacity-60",
                  )}
                >
                  <td className="px-3 py-2">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${style.badge}`}
                    >
                      {style.label}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <div className="font-medium text-text-primary">
                      {entry.establecimiento}
                    </div>
                    <div className="text-[11px] text-text-muted md:hidden">
                      {entry.direccion}
                    </div>
                  </td>
                  <td className="hidden max-w-[200px] truncate px-3 py-2 text-text-secondary md:table-cell">
                    {entry.direccion}
                  </td>
                  <td className="px-3 py-2 text-text-secondary">
                    {entry.mesa_2022 || "—"}
                  </td>
                  <td className="px-3 py-2 text-text-secondary">
                    {entry.mesa_2026 || "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
