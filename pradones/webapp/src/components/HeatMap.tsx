import { useEffect, useRef, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
  LayersControl,
} from "react-leaflet";
import L from "leaflet";
import "leaflet.heat";
import { cn } from "@/lib/cn";
import type { Mesa } from "@/types/padron";

interface HeatMapProps {
  mesas: Mesa[];
  selectedMesa: Mesa | null;
  userLocation: { lat: number; lng: number } | null;
  onMesaClick: (mesa: Mesa) => void;
}

const LA_MATANZA_CENTER: [number, number] = [-34.905, -58.592];

const ZONA_COLORS = [
  "#ef4444", "#f97316", "#f59e0b", "#eab308", "#84cc16",
  "#22c55e", "#14b8a6", "#06b6d4", "#0ea5e9", "#3b82f6",
  "#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899",
  "#f43f5e", "#fb923c", "#fbbf24", "#a3e635", "#34d399",
  "#2dd4bf", "#22d3ee", "#38bdf8", "#818cf8", "#a78bfa",
  "#c084fc", "#e879f9", "#f472b6", "#fb7185", "#fdba74",
];

function getZonaColor(zona: number): string {
  if (zona <= 0 || zona > 30) return "#64748b";
  return ZONA_COLORS[zona - 1];
}

function createMesaIcon(mesa: Mesa) {
  const color = getZonaColor(mesa.zona);
  const size = Math.round(12 + Math.min(mesa.votantes / 4, 16));
  return new L.DivIcon({
    className: "",
    html: `<div style="
      background:${color};
      border:2px solid rgba(255,255,255,0.9);
      border-radius:50%;
      width:${size}px;
      height:${size}px;
      box-shadow:0 0 ${Math.round(size * 0.5)}px ${color}90;
      display:flex;
      align-items:center;
      justify-content:center;
      font-size:${Math.max(8, size - 10)}px;
      font-weight:bold;
      color:#fff;
      text-shadow:0 1px 2px rgba(0,0,0,0.6);
    ">${mesa.votantes >= 20 ? mesa.votantes : ""}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function createSelectedIcon() {
  return new L.DivIcon({
    className: "",
    html: `<div style="
      background:#fff;
      border:3px solid #f59e0b;
      border-radius:50%;
      width:26px;
      height:26px;
      box-shadow:0 0 24px #f59e0b, 0 0 48px #f59e0b40;
    "></div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

const userIcon = new L.DivIcon({
  className: "",
  html: `<div style="background:#22c55e;border:3px solid #fff;border-radius:50%;width:16px;height:16px;box-shadow:0 0 16px #22c55e;"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

function HeatLayer({ mesas, visible }: { mesas: Mesa[]; visible: boolean }) {
  const map = useMap();
  const heatLayerRef = useRef<L.HeatLayer | null>(null);

  useEffect(() => {
    if (heatLayerRef.current) {
      map.removeLayer(heatLayerRef.current);
      heatLayerRef.current = null;
    }

    if (!visible) return;

    const points: [number, number, number][] = mesas.map((m) => [
      m.lat,
      m.lng,
      m.votantes,
    ]);

    heatLayerRef.current = L.heatLayer(points, {
      radius: 30,
      blur: 20,
      maxZoom: 15,
      max: Math.max(...mesas.map((m) => m.votantes)),
      gradient: {
        0.2: "#1e40af",
        0.4: "#3b82f6",
        0.6: "#22c55e",
        0.8: "#f59e0b",
        1.0: "#ef4444",
      },
    });

    heatLayerRef.current.addTo(map);

    return () => {
      if (heatLayerRef.current) {
        map.removeLayer(heatLayerRef.current);
      }
    };
  }, [map, mesas, visible]);

  return null;
}

function FlyToSelected({ mesa }: { mesa: Mesa | null }) {
  const map = useMap();

  useEffect(() => {
    if (mesa) {
      map.flyTo([mesa.lat, mesa.lng], 15, { duration: 1 });
    }
  }, [map, mesa]);

  return null;
}

function getDistance(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function findNearestMesa(
  lat: number,
  lng: number,
  mesas: Mesa[],
): Mesa | null {
  let nearest: Mesa | null = null;
  let minDist = Infinity;
  for (const mesa of mesas) {
    const d = getDistance(lat, lng, mesa.lat, mesa.lng);
    if (d < minDist) {
      minDist = d;
      nearest = mesa;
    }
  }
  return nearest;
}

export function HeatMap({
  mesas,
  selectedMesa,
  userLocation,
  onMesaClick,
}: HeatMapProps) {
  const [showHeat, setShowHeat] = useState(true);
  const [showLegend, setShowLegend] = useState(false);

  const nearestMesa = userLocation
    ? findNearestMesa(userLocation.lat, userLocation.lng, mesas)
    : null;

  const nearestDistance = userLocation && nearestMesa
    ? getDistance(userLocation.lat, userLocation.lng, nearestMesa.lat, nearestMesa.lng)
    : null;

  const zonaNames = new Map<number, string>();
  for (const m of mesas) {
    if (!zonaNames.has(m.zona)) {
      zonaNames.set(m.zona, m.zona_nombre);
    }
  }
  const sortedZonas = Array.from(zonaNames.entries()).sort((a, b) => a[0] - b[0]);

  return (
    <div className="relative h-full w-full">
      {/* Map controls — floating top-left, offset for mobile menu button */}
      <div className="absolute top-3 left-14 z-[1000] flex flex-wrap items-center gap-2 md:left-[440px]">
        <button
          onClick={() => setShowHeat(!showHeat)}
          className={cn(
            "rounded-lg px-3 py-1.5 text-xs font-medium shadow-lg backdrop-blur-sm transition-colors",
            showHeat
              ? "bg-danger/90 text-white"
              : "bg-surface/80 text-text-secondary hover:text-white",
          )}
        >
          {showHeat ? "Ocultar heatmap" : "Mostrar heatmap"}
        </button>
        <button
          onClick={() => setShowLegend(!showLegend)}
          className={cn(
            "rounded-lg px-3 py-1.5 text-xs font-medium shadow-lg backdrop-blur-sm transition-colors",
            showLegend
              ? "bg-primary-light/90 text-white"
              : "bg-surface/80 text-text-secondary hover:text-white",
          )}
        >
          {showLegend ? "Ocultar leyenda" : "Leyenda zonas"}
        </button>
        {nearestMesa && nearestDistance !== null && (
          <button
            onClick={() => onMesaClick(nearestMesa)}
            className="rounded-lg bg-success/90 px-3 py-1.5 text-xs font-bold text-white shadow-lg backdrop-blur-sm transition-colors hover:bg-success"
          >
            Sede cercana: {nearestMesa.mesa} ({nearestDistance.toFixed(1)} km)
          </button>
        )}
      </div>

      {/* Zona legend — floating below controls */}
      {showLegend && (
        <div className="absolute top-14 left-14 z-[1000] max-w-sm rounded-xl bg-surface/90 p-3 shadow-xl backdrop-blur-md md:left-[440px] md:max-w-lg">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
            {sortedZonas.map(([zona, nombre]) => (
              <div key={zona} className="flex items-center gap-2">
                <span
                  className="inline-block h-3 w-3 shrink-0 rounded-full"
                  style={{ background: getZonaColor(zona) }}
                />
                <span className="truncate text-[10px] text-text-secondary">
                  {zona}. {nombre}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Map — full viewport */}
      <MapContainer
        center={LA_MATANZA_CENTER}
        zoom={10}
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
              attribution='&copy; Esri'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>
        </LayersControl>

        <HeatLayer mesas={mesas} visible={showHeat} />
        <FlyToSelected mesa={selectedMesa} />

        {mesas.map((mesa) => {
          const icon =
            selectedMesa?.mesa === mesa.mesa
              ? createSelectedIcon()
              : createMesaIcon(mesa);

          return (
            <Marker
              key={mesa.mesa}
              position={[mesa.lat, mesa.lng]}
              icon={icon}
              eventHandlers={{ click: () => onMesaClick(mesa) }}
            >
              <Popup>
                <div style={{ color: "#1e293b", minWidth: 220, maxWidth: 300 }}>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 4,
                  }}>
                    <span style={{
                      background: getZonaColor(mesa.zona),
                      borderRadius: "50%",
                      width: 12,
                      height: 12,
                      display: "inline-block",
                      flexShrink: 0,
                    }} />
                    <strong style={{ fontSize: 14 }}>
                      Mesa {mesa.mesa} — {mesa.escuela_sede}
                    </strong>
                  </div>
                  <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>
                    {mesa.direccion}, {mesa.localidad}
                  </div>
                  <div style={{
                    display: "flex",
                    gap: 12,
                    marginBottom: 8,
                    padding: "6px 0",
                    borderTop: "1px solid #e2e8f0",
                    borderBottom: "1px solid #e2e8f0",
                  }}>
                    <div>
                      <div style={{ fontSize: 18, fontWeight: "bold", color: "#3b82f6" }}>
                        {mesa.votantes}
                      </div>
                      <div style={{ fontSize: 10, color: "#94a3b8" }}>votantes</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 18, fontWeight: "bold", color: "#f59e0b" }}>
                        {mesa.escuelas.length}
                      </div>
                      <div style={{ fontSize: 10, color: "#94a3b8" }}>escuelas</div>
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: "#475569", marginBottom: 6 }}>
                    <strong>Escuelas que votan aqui:</strong>
                    <div style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 3,
                      marginTop: 4,
                    }}>
                      {mesa.escuelas.map((esc) => (
                        <span
                          key={esc}
                          style={{
                            background: "#f1f5f9",
                            borderRadius: 4,
                            padding: "1px 6px",
                            fontSize: 10,
                            color: "#334155",
                          }}
                        >
                          {esc}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div style={{
                    fontSize: 11,
                    color: getZonaColor(mesa.zona),
                    fontWeight: "bold",
                  }}>
                    Zona {mesa.zona} — {mesa.zona_nombre}
                  </div>
                  {mesa.mapa && (
                    <a
                      href={mesa.mapa}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: 11, color: "#3b82f6", marginTop: 4, display: "inline-block" }}
                    >
                      Abrir en Google Maps
                    </a>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}

        {userLocation && (
          <Marker
            position={[userLocation.lat, userLocation.lng]}
            icon={userIcon}
          >
            <Popup>Tu ubicacion</Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}
