import { Construction } from "lucide-react";
import styles from "./EnConstruccion.module.css";

interface EnConstruccionProps {
  /** Qué se implementará en esta pantalla. */
  contenido: string;
}

/** Marcador temporal para las pantallas que aún no se implementan. */
export default function EnConstruccion({ contenido }: EnConstruccionProps) {
  return (
    <section className={styles.tarjeta}>
      <span className={styles.icono}>
        <Construction size={22} aria-hidden />
      </span>
      <div>
        <h2 className={styles.titulo}>Pantalla en construcción</h2>
        <p className={styles.texto}>{contenido}</p>
      </div>
    </section>
  );
}
