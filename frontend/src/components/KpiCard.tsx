import type { LucideIcon } from "lucide-react";
import styles from "./KpiCard.module.css";

interface KpiCardProps {
  etiqueta: string;
  valor: string;
  ayuda?: string;
  icono: LucideIcon;
  tono?: "azul" | "verde" | "ambar" | "rojo";
}

/** Indicador principal: un número grande con su explicación. */
export default function KpiCard({
  etiqueta,
  valor,
  ayuda,
  icono: Icono,
  tono = "azul",
}: KpiCardProps) {
  return (
    <article className={styles.tarjeta}>
      <span className={`${styles.icono} ${styles[tono]}`}>
        <Icono size={20} aria-hidden />
      </span>
      <div>
        <p className={styles.etiqueta}>{etiqueta}</p>
        <p className={styles.valor}>{valor}</p>
        {ayuda && <p className={styles.ayuda}>{ayuda}</p>}
      </div>
    </article>
  );
}
