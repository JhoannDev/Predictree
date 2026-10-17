import styles from "./PageHeader.module.css";

interface PageHeaderProps {
  antetitulo: string;
  titulo: string;
  descripcion: string;
}

/** Encabezado estándar de cada pantalla. */
export default function PageHeader({ antetitulo, titulo, descripcion }: PageHeaderProps) {
  return (
    <header className={styles.encabezado}>
      <p className={styles.antetitulo}>{antetitulo}</p>
      <h1 className={styles.titulo}>{titulo}</h1>
      <p className={styles.descripcion}>{descripcion}</p>
    </header>
  );
}
