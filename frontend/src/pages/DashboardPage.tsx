import {
  BedDouble,
  CalendarClock,
  CircleCheck,
  Gauge,
  LoaderCircle,
  RefreshCw,
  TriangleAlert,
  UserX,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { GraficoOcupacion } from "../charts/Graficos";
import { COLORES } from "../charts/estilo";
import ChipRiesgo from "../components/ChipRiesgo";
import { Cargando, ErrorCarga, SinAnalisis } from "../components/Estado";
import GuiaLectura from "../components/GuiaLectura";
import KpiCard from "../components/KpiCard";
import PageHeader from "../components/PageHeader";
import PanelNoche from "../components/PanelNoche";
import SelectorRango from "../components/SelectorRango";
import Tarjeta from "../components/Tarjeta";
import { useCarga } from "../hooks/useCarga";
import { api, mensajeDeError } from "../services/api";
import { obtenerDashboard } from "../services/analisisService";
import type { MetricaResumen, NivelRiesgo } from "../types/analisis";
import {
  formatearDecimal,
  formatearEntero,
  formatearFecha,
  formatearFechaCorta,
  formatearPorcentaje,
} from "../utils/formato";
import local from "./Analisis.module.css";
import estilos from "./Pagina.module.css";

function FilaMetrica({
  titulo,
  detalle,
  valor,
  cumple,
}: {
  titulo: string;
  detalle: string;
  valor: string;
  cumple: boolean;
}) {
  return (
    <div className={estilos.metricaFila}>
      <div className={estilos.metricaTexto}>
        <strong>{titulo}</strong>
        <span>{detalle}</span>
      </div>
      <div style={{ textAlign: "right" }}>
        <div className={estilos.metricaValor}>{valor}</div>
        <span className={`${estilos.chipMeta} ${cumple ? estilos.cumple : estilos.nocumple}`}>
          {cumple ? <CircleCheck size={13} aria-hidden /> : <TriangleAlert size={13} aria-hidden />}
          {cumple ? "Cumple la meta" : "Bajo la meta"}
        </span>
      </div>
    </div>
  );
}

const COLOR_NIVEL: Record<NivelRiesgo, string> = {
  bajo: COLORES.bajo,
  medio: COLORES.medio,
  alto: COLORES.alto,
};

export default function DashboardPage() {
  const [dias, setDias] = useState(90);
  const [fecha, setFecha] = useState<string | null>(null);
  const { datos, cargando, error, recargar } = useCarga(() => obtenerDashboard(dias), [dias]);
  const [ejecutando, setEjecutando] = useState(false);
  const [errorEjecucion, setErrorEjecucion] = useState<string | null>(null);

  async function actualizar() {
    setEjecutando(true);
    setErrorEjecucion(null);
    try {
      await api.post("/analisis/ejecutar", null, { timeout: 120000 });
      recargar();
    } catch (e) {
      setErrorEjecucion(mensajeDeError(e, "No se pudo actualizar el análisis."));
    } finally {
      setEjecutando(false);
    }
  }

  const ejec = datos?.ejecucion;
  const metricas: Record<string, MetricaResumen> = datos?.metricas ?? {};

  return (
    <>
      <PageHeader
        antetitulo="Panel de control"
        titulo="Dashboard"
        acciones={<SelectorRango valor={dias} alCambiar={setDias} />}
        descripcion={
          ejec
            ? `Análisis con datos hasta el ${formatearFecha(ejec.fecha_corte)} · próximos ${ejec.horizonte_dias} días · modelo ${ejec.codigo_version}`
            : "Resumen de predicciones y riesgo por fecha."
        }
      />

      {cargando && <Cargando texto="Cargando el análisis…" />}
      {error && <ErrorCarga mensaje={error} reintentar={recargar} />}
      {datos && !ejec && <SinAnalisis />}

      {datos && ejec && (
        <div className={estilos.pila}>
          <GuiaLectura>
            <p>
              Arriba están las noches que conviene mirar primero. Debajo, los números del periodo y
              la ocupación esperada noche a noche frente a la capacidad del hotel.
            </p>
            <p>
              Todo son estimaciones con un margen de error; PredicTree sugiere, pero no cambia
              reservas ni tarifas.
            </p>
          </GuiaLectura>

          <Tarjeta
            titulo="Fechas con riesgo de overbooking"
            descripcion={`Noches de los próximos ${dias} días con riesgo alto o medio. Una fecha con riesgo alto es una fecha crítica. Haz clic en una fila para ver el detalle.`}
          >
            {datos.proximas_atencion.length === 0 ? (
              <p className={local.vacio}>
                <CircleCheck size={16} aria-hidden /> Ninguna noche de los próximos {dias} días
                llega al riesgo medio. No hay nada que revisar por ahora.
              </p>
            ) : (
              <div className={estilos.tablaWrap}>
                <table className={estilos.tabla}>
                  <thead>
                    <tr>
                      <th>Fecha</th>
                      <th>Nivel de riesgo</th>
                      <th className={estilos.num}>Ocupación esperada</th>
                      <th>Motivo</th>
                      <th className={estilos.num}>Sugerencia de tarifa</th>
                    </tr>
                  </thead>
                  <tbody>
                    {datos.proximas_atencion.map((n) => (
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
                        <td>
                          <ChipRiesgo nivel={n.nivel_riesgo} />
                        </td>
                        <td className={estilos.num}>
                          {formatearPorcentaje(n.porcentaje_ocupacion)}
                          <span className={estilos.suave}>
                            {" "}
                            · ≈ {formatearEntero(n.ocupacion_esperada)} de {n.capacidad} hab.
                          </span>
                        </td>
                        <td className={estilos.suave}>
                          {n.eventos.length
                            ? n.eventos.join(", ")
                            : "Ocupación cerca de la capacidad"}
                        </td>
                        <td className={estilos.num}>
                          {n.tipo_sugerencia === "incrementar" && n.ajuste_recomendado !== null
                            ? `Sugerencia: subir tarifa ${formatearDecimal(n.ajuste_recomendado, 1)} %`
                            : "Sugerencia: mantener tarifa"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Tarjeta>

          <div className={estilos.kpis} style={{ marginBottom: 0 }}>
            <KpiCard
              etiqueta={`Ocupación esperada · ${dias} días`}
              valor={formatearPorcentaje(datos.ocupacion_media_pct)}
              ayuda={`Promedio por noche sobre ${datos.noches[0]?.capacidad ?? 240} habitaciones`}
              icono={BedDouble}
            />
            <KpiCard
              etiqueta="Noche más ocupada"
              valor={formatearPorcentaje(datos.ocupacion_pico_pct)}
              ayuda={datos.fecha_pico ? formatearFecha(datos.fecha_pico) : undefined}
              icono={Gauge}
              tono="ambar"
            />
            <KpiCard
              etiqueta="Noches con riesgo medio o alto"
              valor={`${datos.riesgo.medio + datos.riesgo.alto} de ${datos.noches.length}`}
              ayuda={`${datos.riesgo.alto} crítica${datos.riesgo.alto === 1 ? "" : "s"} (desde ${datos.umbral_alto} %) · ${datos.riesgo.medio} en riesgo medio`}
              icono={CalendarClock}
              tono={datos.riesgo.alto ? "rojo" : "ambar"}
            />
            <KpiCard
              etiqueta="Habitaciones que se esperan perder por noche"
              valor={`≈ ${formatearEntero((datos.habitaciones_en_riesgo ?? 0) / Math.max(1, datos.noches.length))}`}
              ayuda={`Por cancelaciones y no-shows · prob. media de cancelación ${formatearPorcentaje(datos.prob_cancelacion_media_pct)}, de no-show ${formatearPorcentaje(datos.prob_noshow_media_pct)}`}
              icono={UserX}
              tono="ambar"
            />
          </div>

          <Tarjeta
            titulo="Ocupación esperada frente a la capacidad"
            descripcion="Habitaciones reservadas − cancelaciones − no-shows + reservas que aún llegarán, como % de las 240 habitaciones."
            acciones={
              <button
                type="button"
                className={estilos.boton}
                onClick={actualizar}
                disabled={ejecutando}
              >
                {ejecutando ? (
                  <LoaderCircle size={16} aria-hidden />
                ) : (
                  <RefreshCw size={16} aria-hidden />
                )}
                {ejecutando ? "Actualizando…" : "Actualizar análisis"}
              </button>
            }
          >
            {errorEjecucion && <ErrorCarga mensaje={errorEjecucion} />}
            <GraficoOcupacion
              noches={datos.noches}
              umbralMedio={datos.umbral_medio}
              umbralAlto={datos.umbral_alto}
              conBanda
              alSeleccionar={setFecha}
              seleccionada={fecha}
            />
            <p className={estilos.notaChica} style={{ marginTop: 8 }}>
              La franja clara es el margen de error: cuanto más lejana es la fecha, más incierta es
              la estimación. Haz clic en una noche para ver su detalle.
            </p>
          </Tarjeta>

          <div className={estilos.dosColumnas}>
            <Tarjeta
              titulo="Distribución del riesgo por noche"
              descripcion={`${datos.noches.length} noches analizadas`}
            >
              <div
                className={estilos.distribucion}
                role="img"
                aria-label="Distribución de noches por nivel de riesgo"
              >
                {(["bajo", "medio", "alto"] as NivelRiesgo[]).map((nivel) => (
                  <div
                    key={nivel}
                    className={estilos.tramo}
                    style={{ flex: datos.riesgo[nivel], background: COLOR_NIVEL[nivel] }}
                    title={`${nivel}: ${datos.riesgo[nivel]} noches`}
                  />
                ))}
              </div>
              <div className={estilos.listaRiesgo}>
                {(["bajo", "medio", "alto"] as NivelRiesgo[]).map((nivel) => (
                  <div key={nivel}>
                    <ChipRiesgo nivel={nivel} />
                    <span>
                      <strong>{datos.riesgo[nivel]}</strong>{" "}
                      {datos.riesgo[nivel] === 1 ? "noche" : "noches"} ·{" "}
                      {formatearPorcentaje((datos.riesgo[nivel] / datos.noches.length) * 100, 0)}
                    </span>
                  </div>
                ))}
              </div>
            </Tarjeta>

            <Tarjeta
              titulo="Qué tan bueno es el modelo"
              descripcion="Evaluado con llegadas que no vio al entrenar."
            >
              {metricas.cancelacion && (
                <FilaMetrica
                  titulo="Cancelación · F1"
                  detalle={`Meta ${formatearDecimal(metricas.cancelacion.meta)}`}
                  valor={formatearDecimal(metricas.cancelacion.f1)}
                  cumple={metricas.cancelacion.cumple_meta}
                />
              )}
              {metricas.no_show && (
                <FilaMetrica
                  titulo="No-show · F1"
                  detalle={`Meta ${formatearDecimal(metricas.no_show.meta)}`}
                  valor={formatearDecimal(metricas.no_show.f1)}
                  cumple={metricas.no_show.cumple_meta}
                />
              )}
              {metricas.ocupacion && (
                <FilaMetrica
                  titulo="Ocupación · error (MAPE) a 30 días"
                  detalle={`Meta ≤ ${formatearPorcentaje(metricas.ocupacion.meta, 0)}`}
                  valor={formatearPorcentaje(metricas.ocupacion.mape)}
                  cumple={metricas.ocupacion.cumple_meta}
                />
              )}
              <p className={estilos.notaChica} style={{ marginTop: 8 }}>
                F1 mide qué tan bien detecta el modelo las cancelaciones o no-shows (1 es perfecto).
                Las metas vienen del documento de requisitos. Ver por qué no se alcanzan en{" "}
                <Link to="/modelo">Modelo y métricas</Link>.
              </p>
            </Tarjeta>
          </div>

          <p className={estilos.pie}>
            Datos de reservas simulados. PredicTree muestra estimaciones y sugerencias; las
            decisiones las toma el hotel. Última actualización:{" "}
            {ejec.fecha_fin ? formatearFecha(ejec.fecha_fin) : "—"}.
          </p>
        </div>
      )}
      {fecha && <PanelNoche fecha={fecha} alCerrar={() => setFecha(null)} />}
    </>
  );
}
