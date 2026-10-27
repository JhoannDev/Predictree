import type { ReactNode } from "react";
import styles from "./Tarjeta.module.css";

interface TarjetaProps {
  titulo?: string;
  descripcion?: string;
  acciones?: ReactNode;
  children: ReactNode;
}

/** Panel blanco con título; contiene gráficos, tablas o texto. */
export default function Tarjeta({ titulo, descripcion, acciones, children }: TarjetaProps) {
  return (
    <section className={styles.tarjeta}>
      {(titulo || acciones) && (
        <header className={styles.cabecera}>
          <div>
            {titulo && <h2 className={styles.titulo}>{titulo}</h2>}
            {descripcion && <p className={styles.descripcion}>{descripcion}</p>}
          </div>
          {acciones}
        </header>
      )}
      {children}
    </section>
  );
}
