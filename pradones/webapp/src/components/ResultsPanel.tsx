import type { Votante, Mesa, Zona, SearchMode } from "@/types/padron";
import { SEARCH_MODE } from "@/types/padron";

interface ResultsPanelProps {
  results: Votante[];
  matchedZonas: Zona[];
  matchedMesas: Mesa[];
  allMesas: Mesa[];
  searchMode: SearchMode | null;
  query: string;
  onFlyToMesa: (mesa: Mesa) => void;
  onClear: () => void;
}

export function ResultsPanel({
  results,
  matchedZonas,
  matchedMesas,
  allMesas,
  searchMode,
  query,
  onFlyToMesa,
  onClear,
}: ResultsPanelProps) {
  if (!searchMode) return null;

  return (
    <div className="fade-in">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs text-text-muted">Resultados de busqueda</p>
        <button
          onClick={onClear}
          className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-text-muted transition-colors hover:bg-surface-lighter hover:text-text-primary"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          Cerrar
        </button>
      </div>
      {searchMode === SEARCH_MODE.DNI && (
        <DniResults results={results} mesas={allMesas} onFlyToMesa={onFlyToMesa} />
      )}
      {searchMode === SEARCH_MODE.ZONA && (
        <ZonaResults
          zonas={matchedZonas}
          mesas={matchedMesas}
          results={results}
          onFlyToMesa={onFlyToMesa}
        />
      )}
      {searchMode === SEARCH_MODE.SEDE && (
        <SedeResults
          mesas={matchedMesas}
          results={results}
          onFlyToMesa={onFlyToMesa}
        />
      )}
      {searchMode === SEARCH_MODE.ESCUELA && (
        <EscuelaResults
          results={results}
          mesa={matchedMesas[0] ?? null}
          query={query}
          onFlyToMesa={onFlyToMesa}
        />
      )}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-border bg-surface-card p-8 text-center">
      <svg
        className="mb-3 h-10 w-10 text-text-muted"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
        />
      </svg>
      <p className="text-sm text-text-muted">{message}</p>
    </div>
  );
}

function Badge({
  children,
  variant,
}: {
  children: React.ReactNode;
  variant: "blue" | "amber" | "green" | "purple";
}) {
  const colors = {
    blue: "bg-blue-500/15 text-blue-300 border-blue-500/20",
    amber: "bg-amber-500/15 text-amber-300 border-amber-500/20",
    green: "bg-emerald-500/15 text-emerald-300 border-emerald-500/20",
    purple: "bg-purple-500/15 text-purple-300 border-purple-500/20",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${colors[variant]}`}
    >
      {children}
    </span>
  );
}

function InfoRow({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: React.ReactNode;
  valueClass?: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="shrink-0 text-xs text-text-muted">{label}</span>
      <span className={`text-right text-sm font-medium ${valueClass ?? "text-text-primary"}`}>
        {value}
      </span>
    </div>
  );
}

function FlyToButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-primary/20 px-3 py-1.5 text-xs font-medium text-primary-light transition-colors hover:bg-primary/30"
    >
      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
      </svg>
      Ver en mapa
    </button>
  );
}

function DniResults({
  results,
  mesas,
  onFlyToMesa,
}: {
  results: Votante[];
  mesas: Mesa[];
  onFlyToMesa: (mesa: Mesa) => void;
}) {
  if (results.length === 0) {
    return <EmptyState message="No se encontro ningun votante con ese DNI" />;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <h3 className="text-base font-semibold text-text-primary">
          {results.length === 1
            ? "Resultado"
            : `${results.length} resultados`}
        </h3>
        <Badge variant="blue">{results.length}</Badge>
      </div>
      {results.slice(0, 10).map((v) => {
        const vMesa = mesas.find((m) => m.mesa === v.mesa_sede);
        return (
          <div
            key={v.documento}
            className="rounded-xl border border-border bg-surface-card p-5"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-base font-bold text-text-primary">
                  {v.nombre}
                </p>
                <p className="mt-0.5 text-sm text-text-muted">
                  DNI {v.documento}
                </p>
              </div>
              <Badge variant="amber">{v.escuela_code}</Badge>
            </div>
            {vMesa && (
              <>
                <div className="mt-4 space-y-2 rounded-lg border border-border bg-surface p-3">
                  <InfoRow
                    label="Mesa/Sede"
                    value={`Mesa ${vMesa.mesa} — ${vMesa.escuela_sede}`}
                  />
                  <InfoRow
                    label="Direccion"
                    value={`${vMesa.direccion}, ${vMesa.localidad}`}
                  />
                  <InfoRow
                    label="Zona"
                    value={`${vMesa.zona} — ${vMesa.zona_nombre}`}
                    valueClass="text-emerald-400"
                  />
                  {vMesa.mapa && (
                    <a
                      href={vMesa.mapa}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 inline-flex items-center gap-1 text-xs text-primary-light transition-colors hover:text-blue-300"
                    >
                      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                      </svg>
                      Abrir en Google Maps
                    </a>
                  )}
                </div>
                <FlyToButton onClick={() => onFlyToMesa(vMesa)} />
              </>
            )}
            {!vMesa && v.zona === 0 && (
              <div className="mt-3 rounded-lg bg-amber-500/10 px-3 py-2">
                <p className="text-sm text-amber-300">
                  Jubilado/a — Mesa 1 Sede Sindical
                </p>
              </div>
            )}
          </div>
        );
      })}
      {results.length > 10 && (
        <p className="text-center text-xs text-text-muted">
          Mostrando 10 de {results.length}. Refina la busqueda.
        </p>
      )}
    </div>
  );
}

function ZonaResults({
  zonas,
  mesas,
  results,
  onFlyToMesa,
}: {
  zonas: Zona[];
  mesas: Mesa[];
  results: Votante[];
  onFlyToMesa: (mesa: Mesa) => void;
}) {
  if (zonas.length === 0) {
    return <EmptyState message="No se encontro esa zona" />;
  }

  return (
    <div className="space-y-4">
      {zonas.map((zona) => {
        const zonaMesas = mesas.filter((m) => m.zona === zona.zona);
        const zonaVotantes = results.filter((v) => v.zona === zona.zona);

        return (
          <div
            key={zona.zona}
            className="overflow-hidden rounded-xl border border-border bg-surface-card"
          >
            <div className="flex items-center justify-between border-b border-border bg-surface-lighter/50 px-5 py-4">
              <div>
                <h3 className="text-base font-bold text-text-primary">
                  Zona {zona.zona}
                </h3>
                <p className="text-sm text-text-muted">{zona.zona_nombre}</p>
              </div>
              <div className="flex gap-2">
                <Badge variant="blue">{zonaVotantes.length} vot.</Badge>
                <Badge variant="amber">{zonaMesas.length} mesas</Badge>
              </div>
            </div>
            <div className="divide-y divide-border/50">
              {zonaMesas.map((mesa) => {
                const mesaVotantes = zonaVotantes.filter(
                  (v) => v.mesa_sede === mesa.mesa,
                ).length;
                return (
                  <button
                    key={mesa.mesa}
                    onClick={() => onFlyToMesa(mesa)}
                    className="card-hover w-full px-5 py-3.5 text-left"
                  >
                    <div className="flex items-center justify-between">
                      <div className="min-w-0 flex-1">
                        <span className="text-sm font-semibold text-text-primary">
                          Mesa {mesa.mesa} — {mesa.escuela_sede}
                        </span>
                        <p className="mt-0.5 text-xs text-text-muted">
                          {mesa.direccion}, {mesa.localidad}
                        </p>
                      </div>
                      <div className="ml-3 flex shrink-0 gap-2 text-right">
                        <div>
                          <p className="text-sm font-bold text-blue-300">
                            {mesaVotantes}
                          </p>
                          <p className="text-[10px] text-text-muted">vot.</p>
                        </div>
                        <div>
                          <p className="text-sm font-bold text-amber-300">
                            {mesa.escuelas.length}
                          </p>
                          <p className="text-[10px] text-text-muted">esc.</p>
                        </div>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {mesa.escuelas.map((esc) => (
                        <span
                          key={esc}
                          className="rounded bg-surface-lighter px-1.5 py-0.5 text-[10px] text-text-muted"
                        >
                          {esc}
                        </span>
                      ))}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SedeResults({
  mesas,
  results,
  onFlyToMesa,
}: {
  mesas: Mesa[];
  results: Votante[];
  onFlyToMesa: (mesa: Mesa) => void;
}) {
  if (mesas.length === 0) {
    return <EmptyState message="No se encontro esa sede" />;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <h3 className="text-base font-semibold text-text-primary">
          {mesas.length} sede{mesas.length > 1 ? "s" : ""}
        </h3>
        <Badge variant="amber">{mesas.length}</Badge>
      </div>
      {mesas.map((mesa) => {
        const votantes = results.filter(
          (v) => v.mesa_sede === mesa.mesa,
        ).length;
        return (
          <button
            key={mesa.mesa}
            onClick={() => onFlyToMesa(mesa)}
            className="card-hover w-full rounded-xl border border-border bg-surface-card p-5 text-left"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="font-bold text-text-primary">
                  Mesa {mesa.mesa} — {mesa.escuela_sede}
                </p>
                <p className="mt-0.5 text-sm text-text-muted">
                  {mesa.direccion}, {mesa.localidad}
                </p>
              </div>
              <Badge variant="blue">{votantes} vot.</Badge>
            </div>
            <div className="mt-3 flex flex-wrap gap-1">
              {mesa.escuelas.map((esc) => (
                <span
                  key={esc}
                  className="rounded bg-surface-lighter px-2 py-0.5 text-xs text-text-muted"
                >
                  {esc}
                </span>
              ))}
            </div>
            <p className="mt-3 text-xs text-emerald-400">
              Zona {mesa.zona} — {mesa.zona_nombre}
            </p>
          </button>
        );
      })}
    </div>
  );
}

function EscuelaResults({
  results,
  mesa,
  query,
  onFlyToMesa,
}: {
  results: Votante[];
  mesa: Mesa | null;
  query: string;
  onFlyToMesa: (mesa: Mesa) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <h3 className="text-base font-semibold text-text-primary">
          Escuela {query.toUpperCase()}
        </h3>
        <Badge variant="purple">{results.length} vot.</Badge>
      </div>

      {mesa && (
        <div className="rounded-xl border border-border bg-surface-card p-5">
          <p className="mb-2 text-xs font-medium tracking-wider text-text-muted uppercase">
            Sede de votacion
          </p>
          <p className="text-base font-bold text-text-primary">
            Mesa {mesa.mesa} — {mesa.escuela_sede}
          </p>
          <p className="mt-1 text-sm text-text-muted">
            {mesa.direccion}, {mesa.localidad}
          </p>
          <p className="mt-2 text-xs text-emerald-400">
            Zona {mesa.zona} — {mesa.zona_nombre}
          </p>
          <div className="mt-3 flex flex-wrap gap-1">
            {mesa.escuelas.map((esc) => (
              <span
                key={esc}
                className="rounded border border-border bg-surface px-2 py-0.5 text-xs text-text-muted"
              >
                {esc}
              </span>
            ))}
          </div>
          {mesa.mapa && (
            <a
              href={mesa.mapa}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex items-center gap-1 text-xs text-primary-light transition-colors hover:text-blue-300"
            >
              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
              </svg>
              Abrir en Google Maps
            </a>
          )}
          <FlyToButton onClick={() => onFlyToMesa(mesa)} />
        </div>
      )}

      {results.length > 0 && (
        <div className="rounded-xl border border-border bg-surface-card p-5">
          <p className="mb-3 text-xs font-medium tracking-wider text-text-muted uppercase">
            Votantes ({results.length})
          </p>
          {results.length <= 100 ? (
            <div className="max-h-72 space-y-1.5 overflow-y-auto pr-1">
              {results.map((v) => (
                <div
                  key={v.documento}
                  className="flex items-baseline justify-between rounded-lg px-2 py-1.5 transition-colors hover:bg-surface-lighter"
                >
                  <span className="text-sm text-text-primary">{v.nombre}</span>
                  <span className="ml-2 shrink-0 text-xs text-text-muted">
                    {v.documento}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-amber-300">
              Demasiados resultados. Refina la busqueda.
            </p>
          )}
        </div>
      )}

      {results.length === 0 && !mesa && (
        <EmptyState message="No se encontro esa escuela en el padron" />
      )}
    </div>
  );
}
