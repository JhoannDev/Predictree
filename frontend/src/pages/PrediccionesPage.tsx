import {
  Ban,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  ListChecks,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
  UserX,
} from "lucide-react";
import { Fragment, useState } from "react";
import { Link } from "react-router-dom";
import { GraficoBarrasHorizontales, GraficoColumnas } from "../charts/Graficos";
import { COLORES } from "../charts/estilo";
import ChipRiesgo from "../components/ChipRiesgo";
import { Cargando, ErrorCarga } from "../components/Estado";
import KpiCard from "../components/KpiCard";
import PageHeader from "../components/PageHeader";
import GuiaLectura from "../components/GuiaLectura";
import Tarjeta from "../components/Tarjeta";
import { useCarga } from "../hooks/useCarga";
import { obtenerPredicciones, obtenerResumenPredicciones } from "../services/analisisService";
import type { FiltrosPredicciones, Prediccion } from "../types/analisis";
import {
  etiquetaCategoria,
  probabilidadesVisibles,
  formatearDecimal,
  formatearEntero,
  formatearFecha,
  formatearPorcentaje,
  formatearSoles,
} from "../utils/formato";
import estilos from "./Pagina.module.css";
import local from "./PrediccionesPage.module.css";

/** Palabra para el tamaño del efecto de un dato (en puntos porcentuales). */
function intensidad(pts: number): string {
  const m = Math.abs(pts);
  return m >= 10 ? "mucho" : m >= 3 ? "bastante" : "un poco";
}

function BarraPct({ valor, maximo, color }: { valor: number; maximo: number; color: string }) {
  return (
    <div className={local.pctCelda}>
      <div className={local.pista} aria-hidden>
        <div
          className={local.relleno}
          style={{ width: `${Math.min(100, (valor / maximo) * 100)}%`, background: color }}
        />
      </div>
      <strong>{formatearPorcentaje(valor)}</strong>
    </div>
  );
}

function Detalle({ p }: { p: Prediccion }) {
  const prob = probabilidadesVisibles(p.prob_cancelacion_pct, p.prob_noshow_pct);
  return (
    <div className={local.detalleCaja}>
      <div>
        <h3>Probabilidades de esta reserva</h3>
        <div className={local.resumenProb}>
          <div>
            <span>Se presenta</span>
            <strong>{formatearPorcentaje(prob.presenta)}</strong>
          </div>
          <div>
            <span>Cancela</span>
            <strong>{formatearPorcentaje(prob.cancela)}</strong>
          </div>
          <div>
            <span>No se presenta (no-show)</span>
            <strong>{formatearPorcentaje(prob.noshow)}</strong>
          </div>
          <div className={estilos.suave}>
            <span>Reserva hecha el</span>
            <span>{formatearFecha(p.fecha_reserva)}</span>
          </div>
          <div className={estilos.suave}>
            <span>Tarifa por noche</span>
            <span>
              {formatearSoles(p.tarifa_noche)} · {etiquetaCategoria(p.politica_tarifa)}
            </span>
          </div>
        </div>
      </div>
      <div>
        <h3>Por qué el modelo de IA estima este riesgo</h3>
        {p.factores_explicativos.length === 0 && (
          <p className={estilos.suave}>Sin factores destacados.</p>
        )}
        {p.factores_explicativos.map((f) => {
          const sube = f.direccion === "aumenta";
          return (
            <div key={f.variable} className={local.factor}>
              {sube ? (
                <TrendingUp size={16} className={local.sube} aria-hidden />
              ) : (
                <TrendingDown size={16} className={local.baja} aria-hidden />
              )}
              <div>
                <strong>{f.nombre}</strong>
                <small>{f.valor}</small>
              </div>
              <div className={`${local.efecto} ${sube ? local.sube : local.baja}`}>
                <strong>
                  {sube ? "Aumenta" : "Reduce"} el riesgo {intensidad(f.efecto_pct)}
                </strong>
                <small>
                  {f.efecto_pct > 0 ? "+" : "−"}
                  {formatearDecimal(Math.abs(f.efecto_pct), 1)} pts
                </small>
              </div>
            </div>
          );
        })}
        <p className={estilos.notaChica} style={{ marginTop: 8 }}>
          <strong>Cómo leerlo:</strong> cada fila compara esta reserva con una reserva típica del
          hotel, mirando un solo dato a la vez. “Reduce” significa que, por ese dato, tiene menos
          probabilidad de no llegar (cancelar o no presentarse) que una reserva típica; “aumenta”,
          más. Los <em>pts</em> son puntos porcentuales: si una reserva típica tuviera 30 % de
          probabilidad de no llegar y por ese dato bajara a 4 %, serían −26 pts. Como cada dato se
          mide por separado, los pts no suman 100 % ni el total de la reserva.
        </p>
      </div>
    </div>
  );
}

function TabReservas() {
  const [filtros, setFiltros] = useState<FiltrosPredicciones>({
    pagina: 1,
    tamano: 15,
    orden: "prob_cancelacion",
    nivel: "",
    canal: "",
    buscar: "",
  });
  const [abierta, setAbierta] = useState<number | null>(null);
  const resumen = useCarga(obtenerResumenPredicciones);
  const lista = useCarga(() => obtenerPredicciones(filtros), [filtros]);

  const cambiar = (cambio: Partial<FiltrosPredicciones>) => {
    setAbierta(null);
    setFiltros((f) => ({ ...f, pagina: 1, ...cambio }));
  };
  const r = resumen.datos;
  const paginas = lista.datos ? Math.max(1, Math.ceil(lista.datos.total / lista.datos.tamano)) : 1;

  return (
    <div className={estilos.pila}>
      {resumen.error && <ErrorCarga mensaje={resumen.error} reintentar={resumen.recargar} />}
      {r && (
        <>
          <div className={estilos.kpis} style={{ marginBottom: 0 }}>
            <KpiCard
              etiqueta="Reservas evaluadas"
              valor={formatearEntero(r.total)}
              ayuda="Confirmadas, con llegada en los próximos 90 días"
              icono={ListChecks}
            />
            <KpiCard
              etiqueta="Probabilidad media de cancelación"
              valor={formatearPorcentaje(r.prob_cancelacion_media_pct)}
              ayuda="Promedio de todas las reservas"
              icono={Ban}
              tono="ambar"
            />
            <KpiCard
              etiqueta="Probabilidad media de no-show"
              valor={formatearPorcentaje(r.prob_noshow_media_pct)}
              ayuda="Promedio de todas las reservas"
              icono={UserX}
              tono="ambar"
            />
            <KpiCard
              etiqueta="Reservas de riesgo alto"
              valor={formatearEntero(r.por_nivel.alto)}
              ayuda={`Cancelación ≥ ${formatearPorcentaje(r.umbral_cancelacion_pct * 2, 0)} · riesgo medio: ${formatearEntero(r.por_nivel.medio)}`}
              icono={ShieldAlert}
              tono="rojo"
            />
          </div>

          <div className={estilos.dosColumnas}>
            <Tarjeta
              titulo="Distribución de la probabilidad de cancelación"
              descripcion="Cuántas reservas confirmadas tienen cada probabilidad de cancelarse."
            >
              <GraficoColumnas
                datos={r.histograma.map((h) => ({
                  nombre: h.rango.replace(" %", ""),
                  valor: h.reservas,
                }))}
                etiquetaValor="Reservas"
                formatoValor={(v) => formatearEntero(v)}
                alto={230}
                colorDe={(nombre) => {
                  const desde = parseInt(nombre, 10);
                  if (desde >= r.umbral_cancelacion_pct * 2) return COLORES.alto;
                  return desde >= r.umbral_cancelacion_pct ? COLORES.medio : COLORES.bajo;
                }}
              />
              <p className={estilos.notaChica}>
                Debajo de cada columna está la probabilidad de cancelación (en %); sobre la columna,
                cuántas reservas caen en ese tramo. El último tramo reúne las de 35 % o más.
              </p>
              <p className={local.leyendaTramos}>
                <span>
                  <i style={{ background: COLORES.bajo }} aria-hidden /> Riesgo bajo: menos de{" "}
                  {formatearPorcentaje(r.umbral_cancelacion_pct, 0)}
                </span>
                <span>
                  <i style={{ background: COLORES.medio }} aria-hidden /> Riesgo medio:{" "}
                  {formatearPorcentaje(r.umbral_cancelacion_pct, 0)} a menos de{" "}
                  {formatearPorcentaje(r.umbral_cancelacion_pct * 2, 0)}
                </span>
                <span>
                  <i style={{ background: COLORES.alto }} aria-hidden /> Riesgo alto:{" "}
                  {formatearPorcentaje(r.umbral_cancelacion_pct * 2, 0)} o más
                </span>
              </p>
            </Tarjeta>
            <Tarjeta
              titulo="Cancelación esperada por canal"
              descripcion="Probabilidad media de cancelación de las reservas de cada canal."
            >
              <GraficoBarrasHorizontales
                datos={r.por_canal.map((c) => ({
                  nombre: etiquetaCategoria(c.grupo),
                  valor: c.cancelacion,
                }))}
                etiquetaValor="Cancelación media"
              />
            </Tarjeta>
          </div>
        </>
      )}

      <Tarjeta
        titulo="Reservas y su riesgo"
        descripcion="Haz clic en una reserva para ver los factores que explican su predicción."
      >
        <div className={local.filtros}>
          <label className={local.campo}>
            Riesgo de cancelación
            <select
              value={filtros.nivel}
              onChange={(e) => cambiar({ nivel: e.target.value as FiltrosPredicciones["nivel"] })}
            >
              <option value="">Todos</option>
              <option value="alto">Alto</option>
              <option value="medio">Medio</option>
              <option value="bajo">Bajo</option>
            </select>
          </label>
          <label className={local.campo}>
            Canal
            <select value={filtros.canal} onChange={(e) => cambiar({ canal: e.target.value })}>
              <option value="">Todos</option>
              {r?.por_canal.map((c) => (
                <option key={c.grupo} value={c.grupo}>
                  {etiquetaCategoria(c.grupo)}
                </option>
              ))}
            </select>
          </label>
          <label className={local.campo}>
            Ordenar por
            <select
              value={filtros.orden}
              onChange={(e) => cambiar({ orden: e.target.value as FiltrosPredicciones["orden"] })}
            >
              <option value="prob_cancelacion">Mayor prob. de cancelación</option>
              <option value="prob_noshow">Mayor prob. de no-show</option>
              <option value="llegada">Fecha de llegada</option>
              <option value="importe">Mayor importe</option>
            </select>
          </label>
          <label className={local.campo}>
            Código de reserva
            <input
              type="search"
              placeholder="Buscar…"
              value={filtros.buscar}
              onChange={(e) => cambiar({ buscar: e.target.value })}
            />
          </label>
        </div>

        {lista.cargando && !lista.datos && <Cargando texto="Cargando predicciones…" />}
        {lista.error && <ErrorCarga mensaje={lista.error} reintentar={lista.recargar} />}
        {lista.datos && (
          <>
            <div className={estilos.tablaWrap}>
              <table className={estilos.tabla}>
                <thead>
                  <tr>
                    <th aria-label="Detalle" />
                    <th>Reserva</th>
                    <th>Llegada</th>
                    <th>Habitación</th>
                    <th>Canal</th>
                    <th className={estilos.num}>Importe</th>
                    <th className={estilos.num}>Se presenta</th>
                    <th>Cancelación</th>
                    <th>No-show</th>
                    <th>Riesgo</th>
                  </tr>
                </thead>
                <tbody>
                  {lista.datos.items.map((p) => {
                    const abierto = abierta === p.id_reserva;
                    return (
                      <Fragment key={p.id_reserva}>
                        <tr
                          className={local.filaClic}
                          onClick={() => setAbierta(abierto ? null : p.id_reserva)}
                          aria-expanded={abierto}
                        >
                          <td>
                            {abierto ? (
                              <ChevronUp size={16} aria-hidden />
                            ) : (
                              <ChevronDown size={16} aria-hidden />
                            )}
                          </td>
                          <td className={`${estilos.fuerte} ${estilos.nowrap}`}>
                            {p.codigo_reserva}
                          </td>
                          <td className={estilos.nowrap}>
                            {formatearFecha(p.fecha_llegada)}
                            <div className={estilos.notaChica}>
                              {p.noches} {p.noches === 1 ? "noche" : "noches"}
                            </div>
                          </td>
                          <td>
                            {etiquetaCategoria(p.tipo_habitacion)}
                            {p.num_habitaciones > 1 && (
                              <span className={estilos.suave}> · {p.num_habitaciones} hab.</span>
                            )}
                          </td>
                          <td>{etiquetaCategoria(p.canal_reserva)}</td>
                          <td className={estilos.num}>{formatearSoles(p.importe_total)}</td>
                          <td className={estilos.num}>
                            {formatearPorcentaje(
                              probabilidadesVisibles(p.prob_cancelacion_pct, p.prob_noshow_pct)
                                .presenta,
                            )}
                          </td>
                          <td>
                            <BarraPct
                              valor={p.prob_cancelacion_pct}
                              maximo={50}
                              color={COLORES.serie1}
                            />
                          </td>
                          <td>
                            <BarraPct
                              valor={p.prob_noshow_pct}
                              maximo={15}
                              color={COLORES.serie2}
                            />
                          </td>
                          <td>
                            <ChipRiesgo nivel={p.nivel_riesgo} />
                          </td>
                        </tr>
                        {abierto && (
                          <tr className={local.detalle}>
                            <td colSpan={10}>
                              <Detalle p={p} />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                  {lista.datos.items.length === 0 && (
                    <tr>
                      <td colSpan={10} className={estilos.suave}>
                        No hay reservas con esos filtros.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className={local.paginacion}>
              <span>
                {formatearEntero(lista.datos.total)} reservas · página {lista.datos.pagina} de{" "}
                {paginas}
              </span>
              <div>
                <button
                  type="button"
                  className={estilos.boton}
                  disabled={filtros.pagina <= 1}
                  onClick={() => setFiltros((f) => ({ ...f, pagina: f.pagina - 1 }))}
                >
                  Anterior
                </button>
                <button
                  type="button"
                  className={estilos.boton}
                  disabled={filtros.pagina >= paginas}
                  onClick={() => setFiltros((f) => ({ ...f, pagina: f.pagina + 1 }))}
                >
                  Siguiente <ChevronRight size={14} aria-hidden />
                </button>
              </div>
            </div>
          </>
        )}
      </Tarjeta>
    </div>
  );
}

export default function PrediccionesPage() {
  return (
    <>
      <PageHeader
        antetitulo="Análisis"
        titulo="Predicciones de cancelación y no-show"
        descripcion="Para cada reserva confirmada, qué tan probable es que se presente, cancele o no llegue, y por qué."
      />
      <div className={estilos.pila}>
        <GuiaLectura>
          <p>
            Cada reserva tiene tres probabilidades que suman 100 %: <strong>se presenta</strong>,{" "}
            <strong>cancela</strong> (avisa antes de llegar) y <strong>no-show</strong> (no llega y
            no avisa). El riesgo de la reserva se mide por su probabilidad de cancelación.
          </p>
          <p>
            Haz clic en una reserva para ver los datos que más influyen en su predicción. Para saber
            qué tan confiable es el modelo, mira la página{" "}
            <Link to="/modelo">Modelo y métricas</Link>.
          </p>
        </GuiaLectura>
        <TabReservas />
      </div>
    </>
  );
}
