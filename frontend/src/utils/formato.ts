/** "Usuario Demo" -> "UD" */
export function iniciales(nombre: string | undefined): string {
  if (!nombre) return "?";
  return nombre
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((parte) => parte[0]?.toUpperCase() ?? "")
    .join("");
}

/** "revenue_management" -> "Revenue management" */
export function formatearRol(rol: string | undefined): string {
  if (!rol) return "";
  const texto = rol.replaceAll("_", " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

const MESES_CORTOS = [
  "ene",
  "feb",
  "mar",
  "abr",
  "may",
  "jun",
  "jul",
  "ago",
  "sep",
  "oct",
  "nov",
  "dic",
];
const DIAS_CORTOS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];

function partesDeFecha(iso: string): Date {
  const [a, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(a, m - 1, d);
}

/** "2026-11-17" -> "17 nov 2026" */
export function formatearFecha(iso: string): string {
  const f = partesDeFecha(iso);
  return `${f.getDate()} ${MESES_CORTOS[f.getMonth()]} ${f.getFullYear()}`;
}

/** "2026-11-17" -> "mar 17 nov 2026" */
export function formatearFechaCorta(iso: string): string {
  const f = partesDeFecha(iso);
  return `${DIAS_CORTOS[f.getDay()]} ${f.getDate()} ${MESES_CORTOS[f.getMonth()]} ${f.getFullYear()}`;
}

/** "2026-11-17" -> "17 nov" */
export function formatearDiaMes(iso: string): string {
  const f = partesDeFecha(iso);
  return `${f.getDate()} ${MESES_CORTOS[f.getMonth()]}`;
}

/** 12.345 -> "12,3 %" */
export function formatearPorcentaje(valor: number | null | undefined, decimales = 1): string {
  if (valor === null || valor === undefined) return "—";
  return `${valor.toFixed(decimales).replace(".", ",")}\u00A0%`;
}

/** 0.3145 -> "0,31" */
export function formatearDecimal(valor: number | null | undefined, decimales = 2): string {
  if (valor === null || valor === undefined) return "—";
  return valor.toFixed(decimales).replace(".", ",");
}

/** 1234.5 -> "S/ 1 235" */
export function formatearSoles(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return `S/ ${Math.round(valor).toLocaleString("es-PE")}`;
}

export function formatearEntero(valor: number): string {
  return Math.round(valor).toLocaleString("es-PE");
}

const TEXTOS: Record<string, string> = {
  web_hilton: "Web Hilton",
  ota: "OTA (agencia en línea)",
  agencia_viajes: "Agencia de viajes",
  corporativo: "Corporativo",
  telefono: "Teléfono",
  junior_suite: "Junior Suite",
  no_reembolsable: "No reembolsable",
};

/** "agencia_viajes" -> "Agencia de viajes" */
export function etiquetaCategoria(valor: string): string {
  if (TEXTOS[valor]) return TEXTOS[valor];
  const t = valor.replaceAll("_", " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
}

/**
 * Probabilidades para mostrar: cancelación y no-show se redondean a 1 decimal y "se presenta" es lo que
 * falta para 100, así los tres siempre suman 100,0 aunque el redondeo individual diga otra cosa.
 */
export function probabilidadesVisibles(cancelacion: number, noshow: number) {
  const c = Math.round(cancelacion * 10) / 10;
  const n = Math.round(noshow * 10) / 10;
  return { presenta: Math.round((100 - c - n) * 10) / 10, cancela: c, noshow: n };
}

interface NocheHabitaciones {
  habitaciones_reservadas: number;
  cancelaciones_estimadas: number;
  noshows_estimados: number;
  ocupacion_esperada: number;
}

/**
 * Habitaciones son números enteros: todo se redondea y el "por llegar" absorbe la diferencia para que
 * la cuenta mostrada cuadre exactamente con la ocupación esperada redondeada.
 */
export function desglosarHabitaciones(n: NocheHabitaciones) {
  const reservadas = Math.round(n.habitaciones_reservadas);
  const cancelaciones = Math.round(n.cancelaciones_estimadas);
  const noshows = Math.round(n.noshows_estimados);
  const esperadas = Math.round(n.ocupacion_esperada);
  return {
    reservadas,
    cancelaciones,
    noshows,
    porLlegar: esperadas - (reservadas - cancelaciones - noshows),
    esperadas,
  };
}

/** 1 -> "1 habitación", 5 -> "5 habitaciones" */
export function textoHabitaciones(cantidad: number): string {
  const n = Math.round(cantidad);
  return `${n.toLocaleString("es-PE")} ${n === 1 ? "habitación" : "habitaciones"}`;
}
