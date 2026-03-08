import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/cn";
import {
  SEARCH_MODE,
  type SearchMode,
  type Mesa,
  type Zona,
} from "@/types/padron";

interface SearchBarProps {
  mesas: Mesa[];
  zonas: Zona[];
  escuelas: string[];
  onSearch: (query: string, mode: SearchMode) => void;
}

const MODES = [
  { key: SEARCH_MODE.DNI, label: "DNI", icon: "M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" },
  { key: SEARCH_MODE.ZONA, label: "Zona", icon: "M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" },
  { key: SEARCH_MODE.SEDE, label: "Sede", icon: "M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008zm0 3h.008v.008h-.008v-.008z" },
  { key: SEARCH_MODE.ESCUELA, label: "Escuela", icon: "M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342" },
] as const;

export function SearchBar({
  mesas,
  zonas,
  escuelas,
  onSearch,
}: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>(SEARCH_MODE.DNI);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), mode);
      setShowDropdown(false);
    }
  };

  const handleSelect = (value: string) => {
    setQuery(value);
    setShowDropdown(false);
    onSearch(value, mode);
  };

  const handleModeChange = (newMode: SearchMode) => {
    setMode(newMode);
    setQuery("");
    setShowDropdown(false);
  };

  const getOptions = (): Array<{
    label: string;
    value: string;
    sub?: string;
  }> => {
    const q = query.toLowerCase();
    switch (mode) {
      case SEARCH_MODE.ZONA:
        return zonas
          .filter(
            (z) =>
              !q ||
              z.zona.toString().includes(q) ||
              z.zona_nombre.toLowerCase().includes(q),
          )
          .map((z) => ({
            label: `Zona ${z.zona} — ${z.zona_nombre}`,
            sub: `${z.votantes} votantes · ${z.mesas} mesas · ${z.escuelas} escuelas`,
            value: z.zona.toString(),
          }));
      case SEARCH_MODE.SEDE:
        return mesas
          .filter(
            (m) =>
              !q ||
              m.escuela_sede.toLowerCase().includes(q) ||
              m.direccion.toLowerCase().includes(q) ||
              m.mesa.toString().includes(q),
          )
          .map((m) => ({
            label: `Mesa ${m.mesa} — ${m.escuela_sede}`,
            sub: `${m.direccion}, ${m.localidad} · ${m.votantes} vot.`,
            value: m.mesa.toString(),
          }));
      case SEARCH_MODE.ESCUELA:
        return escuelas
          .filter((e) => !q || e.toLowerCase().includes(q))
          .map((e) => ({ label: e, value: e }));
      default:
        return [];
    }
  };

  const options = showDropdown ? getOptions() : [];
  const showList = mode !== SEARCH_MODE.DNI;

  const placeholder = {
    [SEARCH_MODE.DNI]: "Ingresá un número de documento...",
    [SEARCH_MODE.ZONA]: "Buscá por nombre o número de zona...",
    [SEARCH_MODE.SEDE]: "Buscá por escuela, dirección o mesa...",
    [SEARCH_MODE.ESCUELA]: "Buscá por código de escuela...",
  }[mode];

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-border bg-surface-card p-4"
    >
      <div className="mb-3 flex gap-1.5 overflow-x-auto">
        {MODES.map((m) => (
          <button
            key={m.key}
            type="button"
            onClick={() => handleModeChange(m.key)}
            className={cn(
              "flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-all",
              mode === m.key
                ? "bg-primary text-white shadow-lg shadow-primary/20"
                : "text-text-muted hover:bg-surface-lighter hover:text-text-secondary",
            )}
          >
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d={m.icon}
              />
            </svg>
            {m.label}
          </button>
        ))}
      </div>

      <div className="relative" ref={dropdownRef}>
        <div className="flex gap-2">
          <div className="relative min-w-0 flex-1">
            <svg
              className="absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-text-muted"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
              />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                if (showList) setShowDropdown(true);
              }}
              onFocus={() => {
                if (showList) setShowDropdown(true);
              }}
              placeholder={placeholder}
              className="w-full rounded-lg border border-border bg-surface py-3 pr-4 pl-10 text-sm text-text-primary placeholder:text-text-muted focus:border-primary-light focus:ring-1 focus:ring-primary-light/30 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            className="shrink-0 rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-primary/20 transition-all hover:bg-primary-dark hover:shadow-primary/30 active:scale-[0.98]"
          >
            Buscar
          </button>
        </div>

        {showDropdown && options.length > 0 && (
          <div className="absolute top-full right-0 left-0 z-[10000] mt-2 max-h-72 overflow-y-auto rounded-xl border border-border bg-surface-light shadow-2xl shadow-black/40">
            {options.slice(0, 50).map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => handleSelect(opt.value)}
                className="w-full border-b border-border/50 px-4 py-3 text-left transition-colors last:border-0 hover:bg-surface-lighter"
              >
                <p className="text-sm font-medium text-text-primary">
                  {opt.label}
                </p>
                {opt.sub && (
                  <p className="mt-0.5 text-xs text-text-muted">{opt.sub}</p>
                )}
              </button>
            ))}
            {options.length > 50 && (
              <p className="px-4 py-3 text-center text-xs text-text-muted">
                +{options.length - 50} más — refiná la búsqueda
              </p>
            )}
          </div>
        )}
      </div>
    </form>
  );
}
