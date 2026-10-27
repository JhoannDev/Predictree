import { CircleHelp } from "lucide-react";
import type { ReactNode } from "react";
import estilos from "./GuiaLectura.module.css";

/** Ayuda plegable "cómo leer este apartado", en lenguaje simple. */
export default function GuiaLectura({
  titulo = "Cómo leer este apartado",
  children,
}: {
  titulo?: string;
  children: ReactNode;
}) {
  return (
    <details className={estilos.guia}>
      <summary>
        <CircleHelp size={16} aria-hidden /> {titulo}
      </summary>
      <div className={estilos.contenido}>{children}</div>
    </details>
  );
}
