import { useState, useEffect } from "react";
import type {
  ComparisonData,
  ComparisonEntry,
  ComparisonStatus,
} from "@/types/comparison";

interface UseComparisonDataReturn {
  data: ComparisonData | null;
  loading: boolean;
  filteredEntries: ComparisonEntry[];
  statusFilter: ComparisonStatus | "todas";
  setStatusFilter: (s: ComparisonStatus | "todas") => void;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  selectedEntry: ComparisonEntry | null;
  setSelectedEntry: (e: ComparisonEntry | null) => void;
}

export function useComparisonData(): UseComparisonDataReturn {
  const [data, setData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<
    ComparisonStatus | "todas"
  >("todas");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedEntry, setSelectedEntry] = useState<ComparisonEntry | null>(
    null,
  );

  useEffect(() => {
    fetch("/comparison.json")
      .then((r) => r.json())
      .then((d: ComparisonData) => {
        setData(d);
        setLoading(false);
      });
  }, []);

  const filteredEntries = data
    ? data.entries.filter((entry) => {
        // Status filter
        if (statusFilter !== "todas" && entry.estado !== statusFilter) {
          return false;
        }
        // Text search
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase().trim();
          return (
            entry.establecimiento.toLowerCase().includes(q) ||
            entry.direccion.toLowerCase().includes(q) ||
            (entry.mesa_2022 && entry.mesa_2022.toLowerCase().includes(q)) ||
            (entry.mesa_2026 && entry.mesa_2026.toLowerCase().includes(q)) ||
            (entry.localidad && entry.localidad.toLowerCase().includes(q)) ||
            (entry.zona_nombre_2022 &&
              entry.zona_nombre_2022.toLowerCase().includes(q))
          );
        }
        return true;
      })
    : [];

  return {
    data,
    loading,
    filteredEntries,
    statusFilter,
    setStatusFilter,
    searchQuery,
    setSearchQuery,
    selectedEntry,
    setSelectedEntry,
  };
}
