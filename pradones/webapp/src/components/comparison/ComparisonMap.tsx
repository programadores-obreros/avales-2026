import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
  LayersControl,
} from "react-leaflet";
import L from "leaflet";
import { COMPARISON_STATUS } from "@/types/comparison";
import type { ComparisonEntry, ComparisonStatus } from "@/types/comparison";

interface ComparisonMapProps {
  entries: ComparisonEntry[];
  selectedEntry: ComparisonEntry | null;
  onMarkerClick: (entry: ComparisonEntry) => void;
}

const LA_MATANZA_CENTER: [number, number] = [-34.905, -58.592];

const STATUS_COLORS: Record<ComparisonStatus, string> = {
  [COMPARISON_STATUS.MANTIENE]: "#f59e0b",
  [COMPARISON_STATUS.NUEVA]: "#10b981",
  [COMPARISON_STATUS.ELIMINADA]: "#ef4444",
};

const STATUS_LABELS: Record<ComparisonStatus, string> = {
  [COMPARISON_STATUS.MANTIENE]: "Se mantiene",
  [COMPARISON_STATUS.NUEVA]: "Nueva 2026",
  [COMPARISON_STATUS.ELIMINADA]: "Eliminada",
};

function createStatusIcon(estado: ComparisonStatus, isSelected: boolean) {
  const color = STATUS_COLORS[estado];
  const size = isSelected ? 22 : 14;
  const border = isSelected ? "3px solid #fff" : "2px solid rgba(255,255,255,0.8)";
  const shadow = isSelected
    ? `0 0 20px ${color}, 0 0 40px ${color}40`
    : `0 0 8px ${color}90`;

  return new L.DivIcon({
    className: "",
    html: `<div style="
      background:${color};
      border:${border};
      border-radius:50%;
      width:${size}px;
      height:${size}px;
      box-shadow:${shadow};
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function FlyToEntry({ entry }: { entry: ComparisonEntry | null }) {
  const map = useMap();

  useEffect(() => {
    if (entry?.lat != null && entry?.lng != null && !isNaN(entry.lat) && !isNaN(entry.lng)) {
      const size = map.getSize();
      // Skip flyTo if the map container is not visible (0x0 dimensions)
      if (size.x === 0 || size.y === 0) return;
      map.flyTo([entry.lat, entry.lng], 15, { duration: 1 });
    }
  }, [map, entry]);

  return null;
}

export function ComparisonMap({
  entries,
  selectedEntry,
  onMarkerClick,
}: ComparisonMapProps) {
  const entriesWithCoords = entries.filter(
    (e) => e.lat != null && e.lng != null && !isNaN(e.lat) && !isNaN(e.lng),
  );

  return (
    <div className="relative h-full w-full">
      {/* Legend */}
      <div className="absolute top-3 left-3 z-[1000] flex gap-3 rounded-lg bg-surface/90 px-3 py-2 text-xs backdrop-blur-sm">
        {Object.entries(STATUS_COLORS).map(([status, color]) => (
          <div key={status} className="flex items-center gap-1.5">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ background: color }}
            />
            <span className="text-text-secondary">
              {STATUS_LABELS[status as ComparisonStatus]}
            </span>
          </div>
        ))}
      </div>

      <MapContainer
        center={LA_MATANZA_CENTER}
        zoom={11}
        scrollWheelZoom={true}
        className="h-full w-full"
        zoomControl={false}
      >
        <LayersControl position="topright">
          <LayersControl.BaseLayer name="Oscuro">
            <TileLayer
              attribution='&copy; <a href="https://carto.com">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer checked name="Calles">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org">OSM</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Satelite">
            <TileLayer
              attribution="&copy; Esri"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>
        </LayersControl>

        <FlyToEntry entry={selectedEntry} />

        {entriesWithCoords.map((entry) => (
          <Marker
            key={entry.id}
            position={[entry.lat!, entry.lng!]}
            icon={createStatusIcon(
              entry.estado,
              selectedEntry?.id === entry.id,
            )}
            eventHandlers={{ click: () => onMarkerClick(entry) }}
          >
            <Popup>
              <div style={{ color: "#1e293b", minWidth: 200, maxWidth: 280 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 4,
                  }}
                >
                  <span
                    style={{
                      background: STATUS_COLORS[entry.estado],
                      borderRadius: "50%",
                      width: 10,
                      height: 10,
                      display: "inline-block",
                      flexShrink: 0,
                    }}
                  />
                  <strong style={{ fontSize: 13 }}>
                    {entry.establecimiento}
                  </strong>
                </div>
                <div
                  style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}
                >
                  {entry.direccion}
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 12,
                    padding: "6px 0",
                    borderTop: "1px solid #e2e8f0",
                    borderBottom: "1px solid #e2e8f0",
                    marginBottom: 6,
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#94a3b8",
                        marginBottom: 2,
                      }}
                    >
                      Mesa 2022
                    </div>
                    <div style={{ fontSize: 14, fontWeight: "bold" }}>
                      {entry.mesa_2022 || "—"}
                    </div>
                  </div>
                  <div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#94a3b8",
                        marginBottom: 2,
                      }}
                    >
                      Mesa 2026
                    </div>
                    <div style={{ fontSize: 14, fontWeight: "bold" }}>
                      {entry.mesa_2026 || "—"}
                    </div>
                  </div>
                </div>
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: "bold",
                    color: STATUS_COLORS[entry.estado],
                  }}
                >
                  {STATUS_LABELS[entry.estado]}
                </div>
                {entry.zona_nombre_2022 && (
                  <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>
                    Zona 2022: {entry.zona_nombre_2022}
                  </div>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
