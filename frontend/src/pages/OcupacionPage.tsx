import { BedDouble, CalendarClock, Gauge, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { GraficoOcupacion } from "../charts/Graficos";
import ChipRiesgo from "../components/ChipRiesgo";
import { Cargando, ErrorCarga, SinAnalisis } from "../components/Estado";
import GuiaLectura from "../components/GuiaLectura";
import KpiCard from "../components/KpiCard";
import PageHeader from "../components/PageHeader";
import PanelNoche from "../components/PanelNoche";
import SelectorRango from "../components/SelectorRango";
import Tarjeta from "../components/Tarjeta";
import { useCarga } from "../hooks/useCarga";
import { obtenerOcupacion } from "../services/analisisService";
import {
  desglosarHabitaciones,
  formatearEntero,
  formatearFecha,
  formatearFechaCorta,
  formatearPorcentaje,
} from "../utils/formato";
import local from "./Analisis.module.css";
import estilos from "./Pagina.module.css";

export default function OcupacionPage() {
  const [dias, setDias] = useState(90);
  const [fecha, setFecha] = useState<string | null>(null);
  const { datos, cargando, error, recargar } = useCarga(() => obtenerOcupacion(dias), [dias]);
  const noches = datos?.noches ?? [];

  const media = noches.length
    ? noches.reduce((a, n) => a + n.porcentaje_ocupacion, 0) / noches.length
    : 0;
  const pico = noches.length
    ? noches.reduce((a, n) => (n.porcentaje_ocupacion > a.porcentaje_ocupacion ? n : a))
    : null;
  const sobreUmbral = noches.filter((n) => n.nivel_riesgo !== "bajo").length;
  const errorMedio = noches.length
    ? noches.reduce((a, n) => a + n.error_esperado_pct, 0) / noches.length
    : 0;

  return (
    <>
      <PageHeader
        antetitulo="Análisis de ocupación"
        titulo="Ocupación esperada"
        descripcion="Cuántas habitaciones se espera ocupar cada noche frente a las 240 del hotel, y cómo se llega a esa cifra."
      />

      {cargando && !datos && <Cargando texto="Cargando la ocupación…" />}
      {error && <ErrorCarga mensaje={error} reintentar={recargar} />}
      {datos && !datos.ejecucion && <SinAnalisis />}

      {datos?.ejecucion && (
        <div className={estilos.pila}>
          <div className={local.barra}>
            <GuiaLectura>
              <p>
                Cada punto es una noche. La línea azul es la ocupación que se espera y la franja
                clara, el margen de error: cuanto más lejos está la fecha, más ancha es.
              </p>
              <p>
                Las líneas punteadas marcan el riesgo medio ({datos.umbral_medio} %) y alto (
                {datos.umbral_alto} %). Haz clic en una noche, en el gráfico o en la tabla, para ver
                cómo se calculó y qué reservas pesan más.
              </p>
            </GuiaLectura>
            <SelectorRango valor={dias} alCambiar={setDias} />
          </div>

          <div className={estilos.kpis} style={{ marginBottom: 0 }}>
            <KpiCard
              etiqueta={`Ocupación media · ${dias} días`}
              valor={formatearPorcentaje(media)}
              ayuda={`${formatearEntero((media / 100) * 240)} de 240 habitaciones por noche`}
              icono={BedDouble}
            />
            <KpiCard
              etiqueta="Noche más ocupada"
              valor={formatearPorcentaje(pico?.porcentaje_ocupacion)}
              ayuda={pico ? formatearFecha(pico.fecha) : undefined}
              icono={Gauge}
              tono="ambar"
            />
            <KpiCard
              etiqueta="Noches con riesgo medio o alto"
              valor={`${sobreUmbral} de ${noches.length}`}
              ayuda={`Desde ${datos.umbral_medio} % de la capacidad`}
              icono={TriangleAlert}
              tono={sobreUmbral ? "rojo" : "verde"}
            />
            <KpiCard
              etiqueta="Margen de error medio"
              valor={`±${formatearPorcentaje(errorMedio)}`}
              ayuda="Calculado con un periodo de prueba; con datos reales puede variar"
              icono={CalendarClock}
            />
          </div>

          <Tarjeta
            titulo="Ocupación esperada por noche"
            descripcion="Habitaciones reservadas − cancelaciones − no-shows + reservas que aún llegarán, como % de la capacidad."
          >
            <GraficoOcupacion
              noches={noches}
              umbralMedio={datos.umbral_medio}
              umbralAlto={datos.umbral_alto}
              conBanda
              alSeleccionar={setFecha}
              seleccionada={fecha}
            />
          </Tarjeta>

          <Tarjeta
            titulo="Detalle por noche"
            descripcion="De dónde sale la cifra de cada noche. Haz clic en una fila para ver más."
          >
            <div className={`${estilos.tablaWrap} ${local.scroll}`}>
              <table className={estilos.tabla}>
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th className={estilos.num}>Reservadas</th>
                    <th className={estilos.num}>− Cancel.</th>
                    <th className={estilos.num}>− No-show</th>
                    <th className={estilos.num}>+ Por llegar</th>
                    <th className={estilos.num}>Esperadas</th>
                    <th className={estilos.num}>Ocupación</th>
                    <th>Riesgo</th>
                  </tr>
                </thead>
                <tbody>
                  {noches.map((n) => {
                    const h = desglosarHabitaciones(n);
                    return (
                      <tr
                        key={n.fecha}
                        className={`${local.filaClic} ${fecha === n.fecha ? local.filaSel : ""}`}
                        tabIndex={0}
                        onClick={() => setFecha(n.fecha)}
                        onKeyDown={(e) => e.key === "Enter" && setFecha(n.fecha)}
                      >
                        <td className={`${estilos.fuerte} ${estilos.nowrap}`}>
                          {formatearFechaCorta(n.fecha)}
                        </td>
                        <td className={estilos.num}>{h.reservadas}</td>
                        <td className={estilos.num}>−{h.cancelaciones}</td>
                        <td className={estilos.num}>−{h.noshows}</td>
                        <td className={estilos.num}>+{h.porLlegar}</td>
                        <td className={estilos.num}>≈ {h.esperadas}</td>
                        <td className={`${estilos.num} ${estilos.fuerte}`}>
                          {formatearPorcentaje(n.porcentaje_ocupacion)}
                        </td>
                        <td>
                          <ChipRiesgo nivel={n.nivel_riesgo} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Tarjeta>

          <p className={estilos.pie}>
            Las reservas “por llegar” se estiman con la historia del hotel: a esa distancia de la
            noche, cuántas reservas suelen llegar todavía. Datos simulados.
          </p>
        </div>
      )}
      {fecha && <PanelNoche fecha={fecha} alCerrar={() => setFecha(null)} />}
    </>
  );
}
