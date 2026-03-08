import type { AppData } from "@/types/padron";

interface StatsCardsProps {
  data: AppData;
}

export function StatsCards({ data }: StatsCardsProps) {
  const totalVotantes = data.votantes.length;
  const totalMesas = data.mesas.length;
  const totalZonas = data.zonas.length;
  const totalEscuelas = new Set(
    data.votantes
      .map((v) => v.escuela_code)
      .filter((c) => c !== "JUBILADO/A" && c !== "AP. EN SEDE"),
  ).size;

  const stats = [
    { label: "Vot.", value: totalVotantes.toLocaleString("es-AR"), color: "text-blue-400" },
    { label: "Sedes", value: totalMesas.toString(), color: "text-amber-400" },
    { label: "Zonas", value: totalZonas.toString(), color: "text-emerald-400" },
    { label: "Esc.", value: totalEscuelas.toString(), color: "text-purple-400" },
  ];

  return (
    <div className="flex items-center gap-4 rounded-lg border border-border bg-surface-card/60 px-4 py-2">
      {stats.map((stat, i) => (
        <div key={stat.label} className="flex items-center gap-4">
          <div className="text-center">
            <p className={`text-sm font-bold leading-none ${stat.color}`}>{stat.value}</p>
            <p className="mt-0.5 text-[10px] text-text-muted">{stat.label}</p>
          </div>
          {i < stats.length - 1 && (
            <div className="h-6 w-px bg-border" />
          )}
        </div>
      ))}
    </div>
  );
}
