import { TriangleAlert } from "lucide-react";
import type { Estado } from "../types/analisis";
import { formatearFecha } from "../utils/formato";
import styles from "./AvisoFecha.module.css";

/**
 * Avisa cuando la fecha de los datos no cuadra con la fecha de hoy (hora del hotel) o cuando el
 * reloj del equipo parece mal puesto. Las predicciones siempre se calculan con la fecha de corte
 * de los datos, no con el reloj, así que el aviso es solo informativo.
 */
function mensajeFecha(e: Estado): string | null {
  if (!e.fecha_corte || !e.hoy) return null;
  const corte = formatearFecha(e.fecha_corte);
  const hoy = formatearFecha(e.hoy);
  const reloj =
    e.reloj_equipo_correcto === false
      ? " Además, el reloj del equipo no coincide con la hora de internet: conviene corregirlo."
      : "";
  if (e.estado_fecha === "desactualizado")
    return `Los datos llegan hasta el ${corte} y hoy es ${hoy}. Las predicciones corresponden al ${corte}: carga los datos más recientes para que reflejen la situación actual.${reloj}`;
  if (e.estado_fecha === "adelantado")
    return `La fecha de los datos (${corte}) es posterior a la de hoy (${hoy}). Revisa que los datos cargados y el reloj del equipo sean correctos.${reloj}`;
  if (e.reloj_equipo_correcto === false)
    return `El reloj del equipo no coincide con la hora de internet (hoy es ${hoy}). Conviene corregirlo para que los avisos de fecha sean fiables.`;
  return null;
}

export default function AvisoFecha({ estado }: { estado: Estado | null }) {
  const mensaje = estado ? mensajeFecha(estado) : null;
  if (!mensaje) return null;
  return (
    <p className={styles.aviso} role="status">
      <TriangleAlert size={18} aria-hidden />
      <span>
        <strong>Fecha de los datos.</strong> {mensaje}
      </span>
    </p>
  );
}
