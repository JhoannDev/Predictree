import {
  CalendarClock,
  BrainCircuit,
  CalendarDays,
  ChartColumn,
  FileText,
  FileUp,
  LayoutGrid,
  type LucideIcon,
  Tag,
  TriangleAlert,
} from "lucide-react";

export interface ItemNavegacion {
  ruta: string;
  etiqueta: string;
  grupo: string;
  icono: LucideIcon;
}

/** Menú lateral. Para agregar una pantalla: añádela aquí y su ruta en App.tsx. */
export const navegacion: ItemNavegacion[] = [
  { ruta: "/dashboard", etiqueta: "Dashboard", grupo: "General", icono: LayoutGrid },
  { ruta: "/predicciones", etiqueta: "Predicciones", grupo: "Análisis", icono: ChartColumn },
  { ruta: "/ocupacion", etiqueta: "Ocupación esperada", grupo: "Análisis", icono: CalendarDays },
  { ruta: "/riesgo", etiqueta: "Riesgo de overbooking", grupo: "Análisis", icono: TriangleAlert },
  {
    ruta: "/fechas-criticas",
    etiqueta: "Fechas críticas",
    grupo: "Seguimiento",
    icono: CalendarClock,
  },
  { ruta: "/tarifas", etiqueta: "Sugerencias de tarifa", grupo: "Seguimiento", icono: Tag },
  { ruta: "/carga-datos", etiqueta: "Carga de datos", grupo: "Datos y reportes", icono: FileUp },
  { ruta: "/reportes", etiqueta: "Reportes", grupo: "Datos y reportes", icono: FileText },
  { ruta: "/modelo", etiqueta: "Modelo y métricas", grupo: "Sistema", icono: BrainCircuit },
];

export const gruposNavegacion = [...new Set(navegacion.map((item) => item.grupo))];
