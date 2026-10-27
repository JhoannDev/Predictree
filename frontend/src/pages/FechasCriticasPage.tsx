import { CircleAlert, TriangleAlert } from "lucide-react";
import { useMemo, useState } from "react";
import ChipRiesgo from "../components/ChipRiesgo";
import { Cargando, ErrorCarga, SinAnalisis } from "../components/Estado";
import GuiaLectura from "../components/GuiaLectura";
import PageHeader from "../components/PageHeader";
import PanelNoche from "../components/PanelNoche";
import Tarjeta from "../components/Tarjeta";
import { useCarga } from "../hooks/useCarga";
import { obtenerRiesgo } from "../services/analisisService";
import type { Noche } from "../types/analisis";
import { formatearFechaCorta, formatearPorcentaje, formatearSoles } from "../utils/formato";
import local from "./Analisis.module.css";
import estilos from "./Pagina.module.css";

const MESES = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];
const DIAS = ["L", "M", "M", "J", "V", "S", "D"];

interface Mes {
  clave: string;
  titulo: string;
  /** Huecos iniciales para alinear con el día de la semana (lunes primero). */
  huecos: number;
  dias: { dia: number; noche?: Noche }[];
}

function armarMeses(noches: Noche[]): Mes[] {
  const porFecha = new Map(noches.map((n) => [n.fecha, n]));
  const meses: Mes[] = [];
  const claves = [...new Set(noches.map((n) => n.fecha.slice(0, 7)))];
  for (const clave of claves) {
    const [a, m] = clave.split("-").map(Number);
    const ultimo = new Date(a, m, 0).getDate();
    const primero = new Date(a, m - 1, 1).getDay(); // 0 = domingo
    meses.push({
      clave,
      titulo: `${MESES[m - 1]} ${a}`,
      huecos: (primero + 6) % 7,
      dias: Array.from({ length: ultimo }, (_, i) => ({
        dia: i + 1,
        noche: porFecha.get(`${clave}-${String(i + 1).padStart(2, "0")}`),
      })),
    });
  }
  return meses;
}

const CLASE_NIVEL = {
  bajo: local.celdaBajo,
  medio: local.celdaMedio,
  alto: local.celdaAlto,
} as const;

export default function FechasCriticasPage() {
  const [fecha, setFecha] = useState<string | null>(null);
  const { datos, cargando, error, recargar } = useCarga(() => obtenerRiesgo(90));
  const meses = useMemo(() => armarMeses(datos?.noches ?? []), [datos]);
  const criticas = datos?.noches.filter((n) => n.nivel_riesgo === "alto") ?? [];
  const medias = datos?.noches.filter((n) => n.nivel_riesgo === "medio") ?? [];

  return (
    <>
      <PageHeader
        antetitulo="Seguimiento"
        titulo="Fechas críticas"
        descripcion="Calendario de las noches con ocupación esperada alta. Haz clic en un día para ver su detalle y la tarifa sugerida."
      />

      {cargando && !datos && <Cargando texto="Cargando el calendario…" />}
      {error && <ErrorCarga mensaje={error} reintentar={recargar} />}
      {datos && !datos.ejecucion && <SinAnalisis />}

      {datos?.ejecucion && (
        <div className={estilos.pila}>
          <GuiaLectura>
            <p>
              Cada día muestra la ocupación esperada. Rojo: fecha crítica (desde {datos.umbral_alto}{" "}
              %). Amarillo: cerca del límite (desde {datos.umbral_medio} %). Verde: sin riesgo. Los
              días en gris quedan fuera del periodo analizado.
            </p>
          </GuiaLectura>

          <Tarjeta
            titulo="Calendario de ocupación esperada"
            descripcion={`${criticas.length} ${criticas.length === 1 ? "fecha crítica" : "fechas críticas"} y ${medias.length} en riesgo medio en los próximos ${datos.noches.length} días.`}
          >
            <div className={local.calendarios}>
              {meses.map((mes) => (
                <div key={mes.clave} className={local.mes}>
                  <h3>{mes.titulo}</h3>
                  <div className={local.rejilla}>
                    {DIAS.map((d, i) => (
                      <span key={i} className={local.diaSemana}>
                        {d}
                      </span>
                    ))}
                    {Array.from({ length: mes.huecos }, (_, i) => (
                      <span key={`h${i}`} className={`${local.celda} ${local.celdaVacia}`} />
                    ))}
                    {mes.dias.map(({ dia, noche }) =>
                      noche ? (
                        <button
                          key={dia}
                          type="button"
                          className={`${local.celda} ${CLASE_NIVEL[noche.nivel_riesgo]} ${fecha === noche.fecha ? local.celdaSel : ""}`}
                          onClick={() => setFecha(noche.fecha)}
                          aria-label={`${formatearFechaCorta(noche.fecha)}: ocupación ${formatearPorcentaje(noche.porcentaje_ocupacion, 0)}, riesgo ${noche.nivel_riesgo}`}
                        >
                          {noche.nivel_riesgo === "alto" && (
                            <TriangleAlert size={11} className={local.celdaIcono} aria-hidden />
                          )}
                          {noche.nivel_riesgo === "medio" && (
                            <CircleAlert size={11} className={local.celdaIcono} aria-hidden />
                          )}
                          <span className={local.celdaDia}>{dia}</span>
                          <span className={local.celdaPct}>
                            {formatearPorcentaje(noche.porcentaje_ocupacion, 0)}
                          </span>
                        </button>
                      ) : (
                        <span key={dia} className={`${local.celda} ${local.celdaFuera}`}>
                          <span className={local.celdaDia}>{dia}</span>
                        </span>
                      ),
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className={local.leyendaCal} style={{ marginTop: 14 }}>
              <span>
                <i className={local.muestra} style={{ background: "var(--color-riesgo-alto)" }} />
                <TriangleAlert size={12} aria-hidden /> Crítica (≥ {datos.umbral_alto} %)
              </span>
              <span>
                <i
                  className={local.muestra}
                  style={{
                    background: "var(--color-riesgo-medio-suave)",
                    border: "1px solid var(--color-riesgo-medio)",
                  }}
                />
                <CircleAlert size={12} aria-hidden /> Riesgo medio (≥ {datos.umbral_medio} %)
              </span>
              <span>
                <i
                  className={local.muestra}
                  style={{ background: "var(--color-riesgo-bajo-suave)" }}
                />
                Sin riesgo
              </span>
              <span>
                <i className={`${local.muestra} ${local.muestraFuera}`} />
                Fuera del periodo analizado
              </span>
            </div>
          </Tarjeta>

          <Tarjeta
            titulo="Fechas a tener presentes"
            descripcion="Fechas críticas y de riesgo medio, con su sugerencia de tarifa informativa."
          >
            <div className={estilos.tablaWrap}>
              <table className={estilos.tabla}>
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th className={estilos.num}>Ocupación</th>
                    <th>Riesgo</th>
                    <th className={estilos.num}>Tarifa sugerida</th>
                    <th>Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  {[...criticas, ...medias].map((n) => (
                    <tr
                      key={n.fecha}
                      className={local.filaClic}
                      tabIndex={0}
                      onClick={() => setFecha(n.fecha)}
                      onKeyDown={(e) => e.key === "Enter" && setFecha(n.fecha)}
                    >
                      <td className={`${estilos.fuerte} ${estilos.nowrap}`}>
                        {formatearFechaCorta(n.fecha)}
                      </td>
                      <td className={estilos.num}>{formatearPorcentaje(n.porcentaje_ocupacion)}</td>
                      <td>
                        <ChipRiesgo nivel={n.nivel_riesgo} />
                      </td>
                      <td className={estilos.num}>
                        {formatearSoles(n.tarifa_sugerida)}
                        {n.ajuste_recomendado !== null && (
                          <span className={estilos.suave}>
                            {" "}
                            {n.ajuste_recomendado === 0
                              ? "(sin cambio)"
                              : `(${n.ajuste_recomendado > 0 ? "+" : ""}${n.ajuste_recomendado.toFixed(1).replace(".", ",")} %)`}
                          </span>
                        )}
                      </td>
                      <td className={estilos.suave}>
                        {n.eventos.length
                          ? n.eventos.join(", ")
                          : "Ocupación cerca de la capacidad"}
                      </td>
                    </tr>
                  ))}
                  {criticas.length + medias.length === 0 && (
                    <tr>
                      <td colSpan={5} className={local.vacio}>
                        No hay fechas críticas ni de riesgo medio en el periodo.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Tarjeta>
        </div>
      )}
      {fecha && <PanelNoche fecha={fecha} alCerrar={() => setFecha(null)} />}
    </>
  );
}
