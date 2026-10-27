import estilos from "./SelectorRango.module.css";

const RANGOS = [7, 30, 60, 90] as const;

/** Botones para elegir cuántos días hacia adelante se muestran. */
export default function SelectorRango({
  valor,
  alCambiar,
  opciones = RANGOS,
}: {
  valor: number;
  alCambiar: (dias: number) => void;
  opciones?: readonly number[];
}) {
  return (
    <div className={estilos.grupo} role="group" aria-label="Periodo mostrado">
      {opciones.map((d) => (
        <button
          key={d}
          type="button"
          aria-pressed={valor === d}
          className={`${estilos.boton} ${valor === d ? estilos.activo : ""}`}
          onClick={() => alCambiar(d)}
        >
          {d} días
        </button>
      ))}
    </div>
  );
}
