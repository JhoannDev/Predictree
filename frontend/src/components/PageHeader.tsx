import type { ReactNode } from "react";
import styles from "./PageHeader.module.css";

interface PageHeaderProps {
  antetitulo: string;
  titulo: string;
  descripcion: string;
  /** Controles a la derecha del título (por ejemplo, el selector de periodo). */
  acciones?: ReactNode;
}

/** Encabezado estándar de cada pantalla. */
export default function PageHeader({ antetitulo, titulo, descripcion, acciones }: PageHeaderProps) {
  return (
    <header className={styles.encabezado}>
      <div className={styles.fila}>
        <div>
          <p className={styles.antetitulo}>{antetitulo}</p>
          <h1 className={styles.titulo}>{titulo}</h1>
        </div>
        {acciones}
      </div>
      <p className={styles.descripcion}>{descripcion}</p>
    </header>
  );
}
