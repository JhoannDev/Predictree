import { CircleAlert, LoaderCircle } from "lucide-react";
import styles from "./Estado.module.css";

export function Cargando({ texto = "Cargando…" }: { texto?: string }) {
  return (
    <div className={styles.caja} role="status">
      <LoaderCircle className={styles.girar} size={20} aria-hidden /> {texto}
    </div>
  );
}

export function ErrorCarga({ mensaje, reintentar }: { mensaje: string; reintentar?: () => void }) {
  return (
    <div className={`${styles.caja} ${styles.error}`} role="alert">
      <CircleAlert size={20} aria-hidden /> {mensaje}
      {reintentar && (
        <button type="button" className={styles.boton} onClick={reintentar}>
          Reintentar
        </button>
      )}
    </div>
  );
}

export function SinAnalisis() {
  return (
    <div className={styles.caja}>
      Aún no hay un análisis. En la carpeta backend ejecuta{" "}
      <code>python -m scripts.entrenar_modelo</code> y luego{" "}
      <code>python -m scripts.ejecutar_analisis</code>.
    </div>
  );
}
