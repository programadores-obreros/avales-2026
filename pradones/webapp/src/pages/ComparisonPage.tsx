import { useState } from "react";
import { Link } from "react-router-dom";
import { useComparisonData } from "@/hooks/useComparisonData";
import { ComparisonStatsCards } from "@/components/comparison/ComparisonStatsCards";
import { ComparisonFilters } from "@/components/comparison/ComparisonFilters";
import { ComparisonTable } from "@/components/comparison/ComparisonTable";
import { ComparisonMap } from "@/components/comparison/ComparisonMap";
import { cn } from "@/lib/cn";
import type { ComparisonEntry } from "@/types/comparison";

function ComparisonPage() {
  const {
    data,
    loading,
    filteredEntries,
    statusFilter,
    setStatusFilter,
    searchQuery,
    setSearchQuery,
    selectedEntry,
    setSelectedEntry,
  } = useComparisonData();

  const [sheetOpen, setSheetOpen] = useState(true);

  const handleEntryClick = (entry: ComparisonEntry) => {
    setSelectedEntry(entry);
    // On mobile, collapse sheet when clicking a card with coords so user can see map flyTo
    if (window.innerWidth < 1024 && entry.lat != null) {
      setSheetOpen(false);
    }
  };

  const handleMarkerClick = (entry: ComparisonEntry) => {
    setSelectedEntry(entry);
    // On mobile, open sheet so user can see the highlighted card
    if (window.innerWidth < 1024) {
      setSheetOpen(true);
    }
  };

  if (loading || !data) {
    return (
      <div className="flex h-dvh items-center justify-center bg-surface">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-primary-light border-t-transparent" />
          <p className="text-text-secondary">Cargando comparación...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* ===== DESKTOP LAYOUT (lg+): unchanged side-by-side ===== */}
      <div className="hidden h-dvh flex-col bg-surface lg:flex">
        {/* Header */}
        <header className="shrink-0 border-b border-border bg-surface-card/80 px-4 py-3 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-lighter text-text-secondary transition-colors hover:text-white"
              aria-label="Volver al padrón"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.75 19.5L8.25 12l7.5-7.5"
                />
              </svg>
            </Link>
            <div>
              <h1 className="text-base font-bold text-white">
                Mesas 2022 vs 2026
              </h1>
              <p className="text-[11px] text-text-muted">
                SUTEBA La Matanza — Comparación de sedes electorales
              </p>
            </div>
            <a
              href="/mesas_2026_la_matanza.xlsx"
              download
              className="ml-auto flex h-8 items-center gap-1.5 rounded-lg bg-primary/20 px-3 text-xs font-medium text-primary-light transition-colors hover:bg-primary/30"
              title="Descargar listado de mesas 2026"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
                />
              </svg>
              XLSX
            </a>
          </div>

          <div className="mt-3">
            <ComparisonStatsCards summary={data.summary} />
          </div>
        </header>

        {/* Body: Table + Map side by side */}
        <div className="flex min-h-0 flex-1">
          <div className="flex w-[60%] flex-col border-r border-border">
            <div className="shrink-0 px-4 pt-3">
              <ComparisonFilters
                statusFilter={statusFilter}
                onStatusChange={setStatusFilter}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                summary={data.summary}
                filteredCount={filteredEntries.length}
              />
            </div>
            <div className="min-h-0 flex-1 px-4 pt-2 pb-4">
              <ComparisonTable
                entries={filteredEntries}
                selectedEntry={selectedEntry}
                onEntryClick={handleEntryClick}
              />
            </div>
          </div>
          <div className="w-[40%]">
            <ComparisonMap
              entries={filteredEntries}
              selectedEntry={selectedEntry}
              onMarkerClick={handleMarkerClick}
            />
          </div>
        </div>
      </div>

      {/* ===== MOBILE LAYOUT (<lg): map background + bottom sheet ===== */}
      <div className="relative h-dvh w-full overflow-hidden lg:hidden">
        {/* Map — full viewport background */}
        <div className="absolute inset-0">
          <ComparisonMap
            entries={filteredEntries}
            selectedEntry={selectedEntry}
            onMarkerClick={handleMarkerClick}
          />
        </div>

        {/* Back button — top left */}
        <Link
          to="/"
          className="absolute top-3 left-3 z-[1100] flex h-10 w-10 items-center justify-center rounded-xl bg-surface/90 text-text-secondary shadow-lg backdrop-blur-sm transition-colors hover:text-white"
          aria-label="Volver al padrón"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15.75 19.5L8.25 12l7.5-7.5"
            />
          </svg>
        </Link>

        {/* Sheet toggle button — top left next to back */}
        <button
          onClick={() => setSheetOpen(!sheetOpen)}
          className="absolute top-3 left-16 z-[1100] flex h-10 items-center gap-1.5 rounded-xl bg-surface/90 px-3 text-text-secondary shadow-lg backdrop-blur-sm transition-all hover:text-white"
          aria-label={sheetOpen ? "Cerrar panel" : "Abrir panel"}
        >
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            {sheetOpen ? (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            ) : (
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
              />
            )}
          </svg>
          <span className="text-xs font-medium">
            {sheetOpen ? "Mapa" : "Lista"}
          </span>
        </button>

        {/* Bottom sheet overlay */}
        <div
          className={cn(
            "absolute inset-x-0 bottom-0 z-[1000] flex max-h-[55dvh] flex-col rounded-t-2xl transition-transform duration-300 ease-in-out",
            sheetOpen ? "translate-y-0" : "translate-y-full",
          )}
        >
          {/* Drag handle */}
          <div
            className="flex shrink-0 cursor-pointer justify-center py-2"
            onClick={() => setSheetOpen(!sheetOpen)}
          >
            <div className="h-1.5 w-12 rounded-full bg-text-muted/40" />
          </div>

          {/* Sheet content */}
          <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto bg-surface/95 px-4 pb-4 backdrop-blur-md">
            {/* Title + stats */}
            <div className="flex items-center justify-between gap-2">
              <h1 className="shrink-0 text-sm font-bold text-white">
                2022 vs 2026
              </h1>
              <a
                href="/mesas_2026_la_matanza.xlsx"
                download
                className="flex h-7 items-center gap-1 rounded-md bg-primary/20 px-2 text-[11px] font-medium text-primary-light"
                title="Descargar XLSX"
              >
                <svg
                  className="h-3.5 w-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
                  />
                </svg>
                XLSX
              </a>
              <div className="min-w-0 flex-1">
                <ComparisonStatsCards summary={data.summary} />
              </div>
            </div>

            {/* Filters */}
            <ComparisonFilters
              statusFilter={statusFilter}
              onStatusChange={setStatusFilter}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              summary={data.summary}
              filteredCount={filteredEntries.length}
            />

            {/* Cards list */}
            <ComparisonTable
              entries={filteredEntries}
              selectedEntry={selectedEntry}
              onEntryClick={handleEntryClick}
            />
          </div>
        </div>
      </div>
    </>
  );
}

export default ComparisonPage;
