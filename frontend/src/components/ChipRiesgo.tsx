import { CircleCheck, CircleAlert, TriangleAlert } from "lucide-react";
import type { NivelRiesgo } from "../types/analisis";
import styles from "./ChipRiesgo.module.css";

const CONFIG = {
  bajo: { texto: "Bajo", icono: CircleCheck },
  medio: { texto: "Medio", icono: CircleAlert },
  alto: { texto: "Alto", icono: TriangleAlert },
} as const;

/** Nivel de riesgo con ícono y texto (nunca solo color). */
export default function ChipRiesgo({ nivel }: { nivel: NivelRiesgo }) {
  const { texto, icono: Icono } = CONFIG[nivel];
  return (
    <span className={`${styles.chip} ${styles[nivel]}`}>
      <Icono size={13} aria-hidden />
      {texto}
    </span>
  );
}
