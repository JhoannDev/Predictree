import { Info, X } from "lucide-react";
import { useEffect } from "react";
import { useCarga } from "../hooks/useCarga";
import { obtenerDetalleNoche } from "../services/analisisService";
import estilos from "../pages/Pagina.module.css";
import type { DetalleNoche } from "../types/analisis";
import {
  etiquetaCategoria,
  desglosarHabitaciones,
  formatearDecimal,
  formatearEntero,
  formatearFecha,
  formatearPorcentaje,
  formatearSoles,
} from "../utils/formato";
import ChipRiesgo from "./ChipRiesgo";
import { Cargando, ErrorCarga } from "./Estado";
import local from "./PanelNoche.module.css";

const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];

function nombreDia(iso: string): string {
  const [a, m, d] = iso.split("-").map(Number);
  return DIAS[new Date(a, m - 1, d).getDay()];
}

/** Frase simple para quien no conoce el modelo: qué se espera y qué conviene mirar. */
function lectura(d: DetalleNoche): string {
  const n = d.noche;
  const libres = Math.max(0, n.capacidad - n.ocupacion_esperada);
  const base = `Se espera ocupar unas ${formatearEntero(n.ocupacion_esperada)} de ${n.capacidad} habitaciones`;
  if (n.nivel_riesgo === "alto") {
    const exceso = Math.max(0, n.exceso_habitaciones);
    return exceso > 0
      ? `${base}: unas ${formatearEntero(exceso)} más que la capacidad. Conviene revisar la disponibilidad y la política de overbooking para esta noche.`
      : `${base}, casi toda la capacidad. Conviene vigilar esta noche de cerca.`;
  }
  if (n.nivel_riesgo === "medio")
    return `${base}; quedarían unas ${formatearEntero(libres)} libres. Está cerca del límite: conviene seguir de cerca las nuevas reservas y cancelaciones.`;
  return `${base}; quedarían unas ${formatearEntero(libres)} libres. No se ve riesgo de overbooking.`;
}

const TEXTO_SUGERENCIA = {
  incrementar: "Subir la tarifa",
  mantener: "Mantener la tarifa",
  promocion: "Evaluar una promoción",
} as const;

function Contenido({ d }: { d: DetalleNoche }) {
  const n = d.noche;
  const hab = desglosarHabitaciones(n);
  const pct = Math.min(130, n.porcentaje_ocupacion);
  return (
    <div className={local.cuerpo}>
      <div className={local.cifra}>
        <div>
          <span className={local.etiqueta}>Ocupación esperada</span>
          <strong className={local.grande}>{formatearPorcentaje(n.porcentaje_ocupacion)}</strong>
          <span className={estilos.notaChica}>
            unas {formatearEntero(n.ocupacion_esperada)} de {n.capacidad} habitaciones (estimado)
          </span>
        </div>
        <ChipRiesgo nivel={n.nivel_riesgo} />
      </div>
      <div className={local.escala} aria-hidden>
        <div className={local.zonaMedio} style={{ left: `${(d.umbral_medio / 130) * 100}%` }} />
        <div className={local.zonaAlto} style={{ left: `${(d.umbral_alto / 130) * 100}%` }} />
        <div className={local.relleno} style={{ width: `${(pct / 130) * 100}%` }} />
      </div>
      <p className={local.leyendaEscala}>
        <span>0 %</span>
        <span>
          Medio {d.umbral_medio} % · Alto {d.umbral_alto} %
        </span>
        <span>130 %</span>
      </p>

      <p className={local.lectura}>{lectura(d)}</p>
      <p className={estilos.notaChica}>
        <strong>Qué tanto puede fallar esta cifra:</strong> faltan {n.dias_anticipacion} días entre
        la fecha de los datos y esta noche. A esa distancia, en las pruebas con fechas pasadas, el
        modelo se desvió en promedio un {formatearPorcentaje(n.error_esperado_pct, 0)}. Por eso la
        ocupación real podría quedar entre {formatearPorcentaje(n.banda_inf_pct, 0)} y{" "}
        {formatearPorcentaje(n.banda_sup_pct, 0)}. Mientras más cerca esté la fecha, más precisa es.
      </p>
      {n.eventos.length > 0 && (
        <p className={local.motivo}>
          <Info size={15} aria-hidden /> Coincide con: {n.eventos.join(", ")}.
        </p>
      )}

      <h3>Cómo sale esta cifra (Habitaciones / Aproximados)</h3>
      <dl className={local.cuenta}>
        <div className={local.destacada}>
          <dt>Habitaciones ya reservadas</dt>
          <dd>{hab.reservadas}</dd>
        </div>
        <div>
          <dt>− Cancelaciones que se estiman</dt>
          <dd>−{hab.cancelaciones}</dd>
        </div>
        <div>
          <dt>− No-shows que se estiman</dt>
          <dd>−{hab.noshows}</dd>
        </div>
        <div>
          <dt>+ Reservas que aún llegarán (estimación según historial)</dt>
          <dd>+{hab.porLlegar}</dd>
        </div>
        <div className={local.total}>
          <dt>= Habitaciones ocupadas (estimado)</dt>
          <dd>≈ {hab.esperadas}</dd>
        </div>
      </dl>

      {n.tipo_sugerencia && (
        <>
          <h3>Sugerencia de tarifa (informativa)</h3>
          <div className={local.sugerencia}>
            <div>
              <span className={local.etiqueta}>{TEXTO_SUGERENCIA[n.tipo_sugerencia]}</span>
              <strong>
                {n.ajuste_recomendado !== null && n.ajuste_recomendado > 0 ? "+" : ""}
                {formatearDecimal(n.ajuste_recomendado ?? 0, 1)} %
              </strong>
            </div>
            <div>
              <span className={local.etiqueta}>Tarifa de referencia</span>
              <strong>{formatearSoles(n.tarifa_referencia)}</strong>
            </div>
            <div>
              <span className={local.etiqueta}>Tarifa sugerida</span>
              <strong>{formatearSoles(n.tarifa_sugerida)}</strong>
            </div>
          </div>
          <p className={estilos.notaChica}>{n.justificacion}</p>
        </>
      )}

      <h3>Reservas que más pesan en esta noche</h3>
      <p className={estilos.notaChica}>
        Las de mayor probabilidad de no llegar. Entre todas las reservas de esta noche se espera que
        unas {formatearEntero(d.habitaciones_en_riesgo_total)} habitaciones no se usen, por
        cancelación o no-show.
      </p>
      <div className={estilos.tablaWrap}>
        <table className={estilos.tabla}>
          <thead>
            <tr>
              <th>Reserva</th>
              <th className={estilos.num}>Cancela</th>
              <th className={estilos.num}>No-show</th>
            </tr>
          </thead>
          <tbody>
            {d.reservas_que_pesan.map((r) => (
              <tr key={r.id_reserva}>
                <td>
                  <span className={estilos.fuerte}>{r.codigo_reserva}</span>
                  <div className={estilos.notaChica}>
                    {etiquetaCategoria(r.tipo_habitacion)}
                    {r.num_habitaciones > 1 ? ` · ${r.num_habitaciones} hab.` : ""} ·{" "}
                    {etiquetaCategoria(r.canal_reserva)} · llega {formatearFecha(r.fecha_llegada)}
                  </div>
                </td>
                <td className={estilos.num}>{formatearPorcentaje(r.prob_cancelacion_pct)}</td>
                <td className={estilos.num}>{formatearPorcentaje(r.prob_noshow_pct)}</td>
              </tr>
            ))}
            {d.reservas_que_pesan.length === 0 && (
              <tr>
                <td colSpan={3} className={estilos.suave}>
                  No hay reservas confirmadas para esta noche.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className={local.aviso}>
        PredicTree solo muestra estimaciones y sugerencias. Las decisiones sobre reservas, tarifas y
        overbooking las toma el hotel.
      </p>
    </div>
  );
}

/** Panel lateral con el detalle de una noche (se usa desde varias pantallas). */
export default function PanelNoche({ fecha, alCerrar }: { fecha: string; alCerrar: () => void }) {
  const { datos, cargando, error, recargar } = useCarga(() => obtenerDetalleNoche(fecha), [fecha]);

  useEffect(() => {
    const alTeclear = (e: KeyboardEvent) => e.key === "Escape" && alCerrar();
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [alCerrar]);

  return (
    <div className={local.fondo} onClick={alCerrar}>
      <aside
        className={local.panel}
        role="dialog"
        aria-modal="true"
        aria-label={`Detalle de la noche del ${formatearFecha(fecha)}`}
        onClick={(e) => e.stopPropagation()}
      >
        <header className={local.cabecera}>
          <div>
            <p className={local.superior}>Detalle de la noche</p>
            <h2>
              {nombreDia(fecha)} {formatearFecha(fecha)}
            </h2>
          </div>
          <button type="button" className={local.cerrar} onClick={alCerrar} aria-label="Cerrar">
            <X size={18} aria-hidden />
          </button>
        </header>
        {cargando && <Cargando />}
        {error && <ErrorCarga mensaje={error} reintentar={recargar} />}
        {datos && <Contenido d={datos} />}
      </aside>
    </div>
  );
}
