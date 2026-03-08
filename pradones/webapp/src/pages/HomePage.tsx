import { useState, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { SearchBar } from "@/components/SearchBar";
import { StatsCards } from "@/components/StatsCards";
import { HeatMap } from "@/components/HeatMap";
import { ResultsPanel } from "@/components/ResultsPanel";
import { useGeolocation } from "@/hooks/useGeolocation";
import { cn } from "@/lib/cn";
import type { AppData, Mesa, SearchMode, Votante, Zona } from "@/types/padron";
import { SEARCH_MODE } from "@/types/padron";

function normalizeEscuelaQuery(raw: string): string {
  const q = raw.toUpperCase().replace(/\s+/g, "");
  if (q.includes("-")) return q;
  const match = q.match(/^([A-Z]+)(\d+)$/);
  if (!match) return q;
  return `${match[1]}-${match[2].padStart(4, "0")}`;
}

export function HomePage() {
  const [data, setData] = useState<AppData | null>(null);
  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState<Votante[]>([]);
  const [matchedZonas, setMatchedZonas] = useState<Zona[]>([]);
  const [matchedMesas, setMatchedMesas] = useState<Mesa[]>([]);
  const [searchMode, setSearchMode] = useState<SearchMode | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedMesa, setSelectedMesa] = useState<Mesa | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const geo = useGeolocation();

  useEffect(() => {
    fetch("/data.json")
      .then((r) => r.json())
      .then((d: AppData) => {
        setData(d);
        setLoading(false);
      });
  }, []);

  const allEscuelas = useMemo(() => {
    if (!data) return [];
    const set = new Set<string>();
    for (const mesa of data.mesas) {
      for (const esc of mesa.escuelas) {
        set.add(esc);
      }
    }
    return Array.from(set).sort();
  }, [data]);

  const handleSearch = (query: string, mode: SearchMode) => {
    if (!data) return;
    setSearchMode(mode);
    setSearchQuery(query);
    setSelectedMesa(null);
    setMatchedZonas([]);
    setMatchedMesas([]);

    const q = query.toLowerCase().trim();

    switch (mode) {
      case SEARCH_MODE.DNI: {
        const found = data.votantes.filter((v) => v.documento.includes(q));
        setResults(found);
        if (found.length > 0) {
          const mesa = data.mesas.find((m) => m.mesa === found[0].mesa_sede);
          if (mesa) setSelectedMesa(mesa);
        }
        break;
      }
      case SEARCH_MODE.ZONA: {
        const zonaNum = parseInt(query, 10);
        const matched = data.zonas.filter(
          (z) =>
            z.zona === zonaNum ||
            z.zona_nombre.toLowerCase().includes(q),
        );
        setMatchedZonas(matched);
        const zonaNumbers = new Set(matched.map((z) => z.zona));
        const zonaMesas = data.mesas.filter((m) => zonaNumbers.has(m.zona));
        setMatchedMesas(zonaMesas);
        setResults(data.votantes.filter((v) => zonaNumbers.has(v.zona)));
        break;
      }
      case SEARCH_MODE.SEDE: {
        const mesaNum = parseInt(query, 10);
        const matched = data.mesas.filter(
          (m) =>
            m.mesa === mesaNum ||
            m.escuela_sede.toLowerCase().includes(q) ||
            m.direccion.toLowerCase().includes(q),
        );
        setMatchedMesas(matched);
        const mesaNumbers = new Set(matched.map((m) => m.mesa));
        setResults(data.votantes.filter((v) => mesaNumbers.has(v.mesa_sede)));
        if (matched.length === 1) setSelectedMesa(matched[0]);
        break;
      }
      case SEARCH_MODE.ESCUELA: {
        const normalized = normalizeEscuelaQuery(query);
        setResults(data.votantes.filter((v) => v.escuela_code === normalized));
        const mesa = data.mesas.find((m) => m.escuelas.includes(normalized));
        if (mesa) {
          setSelectedMesa(mesa);
          setMatchedMesas([mesa]);
        }
        break;
      }
    }
  };

  const handleMesaClick = (mesa: Mesa) => {
    setSelectedMesa(mesa);
  };

  const clearResults = () => {
    setSearchMode(null);
    setResults([]);
    setMatchedZonas([]);
    setMatchedMesas([]);
    setSelectedMesa(null);
    setSearchQuery("");
  };

  const handleFlyToMesa = (mesa: Mesa) => {
    setSelectedMesa(mesa);
    if (window.innerWidth < 768) {
      setPanelOpen(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="flex h-dvh items-center justify-center bg-surface">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-primary-light border-t-transparent" />
          <p className="text-text-secondary">Cargando padrón...</p>
        </div>
      </div>
    );
  }

  const userLocation =
    geo.lat && geo.lng ? { lat: geo.lat, lng: geo.lng } : null;

  return (
    <div className="relative h-dvh w-full overflow-hidden">
      {/* MAP — full viewport background */}
      <div className="absolute inset-0">
        <HeatMap
          mesas={data.mesas}
          selectedMesa={selectedMesa}
          userLocation={userLocation}
          onMesaClick={handleMesaClick}
        />
      </div>

      {/* PANEL TOGGLE — always visible */}
      <button
        onClick={() => setPanelOpen(!panelOpen)}
        className="absolute top-3 left-3 z-[1100] flex h-10 w-10 items-center justify-center rounded-xl bg-surface/90 text-text-primary shadow-lg backdrop-blur-sm transition-all hover:bg-surface-light md:hidden"
        aria-label={panelOpen ? "Cerrar panel" : "Abrir panel"}
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          {panelOpen ? (
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          )}
        </svg>
      </button>

      {/* OVERLAY PANEL */}
      <div
        className={cn(
          "absolute z-[1000] flex flex-col transition-transform duration-300 ease-in-out",
          "inset-x-0 bottom-0 max-h-[70dvh] rounded-t-2xl md:rounded-t-none",
          "md:inset-y-0 md:left-0 md:w-[420px] md:max-h-none",
          panelOpen
            ? "translate-y-0 md:translate-x-0"
            : "translate-y-full md:-translate-x-full",
        )}
      >
        {/* Mobile drag handle */}
        <div className="flex justify-center py-2 md:hidden">
          <div className="h-1.5 w-12 rounded-full bg-text-muted/40" />
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto bg-surface/95 p-4 backdrop-blur-md md:pt-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold text-white">
                SUTEBA La Matanza 2026
              </h1>
              <p className="text-xs text-text-secondary">
                Padrón Electoral — {data.votantes.length.toLocaleString("es-AR")} votantes
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Link
                to="/mesas-2022-2026"
                className="rounded-lg bg-primary/20 px-3 py-2 text-xs font-medium text-primary-light transition-colors hover:bg-primary/30"
              >
                2022 vs 2026
              </Link>
              <button
                onClick={geo.requestLocation}
                disabled={geo.loading}
                className="flex items-center gap-1.5 rounded-lg bg-surface-lighter px-3 py-2 text-xs text-text-secondary transition-colors hover:text-white"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {geo.loading ? "..." : "Ubicarme"}
              </button>
            </div>
          </div>

          <StatsCards data={data} />

          <SearchBar
            mesas={data.mesas}
            zonas={data.zonas}
            escuelas={allEscuelas}
            onSearch={handleSearch}
          />

          <ResultsPanel
            results={results}
            matchedZonas={matchedZonas}
            matchedMesas={matchedMesas}
            allMesas={data.mesas}
            searchMode={searchMode}
            query={searchQuery}
            onFlyToMesa={handleFlyToMesa}
            onClear={clearResults}
          />
        </div>
      </div>
    </div>
  );
}
