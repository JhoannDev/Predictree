import { CircleCheck, TriangleAlert } from "lucide-react";
import { Cargando, ErrorCarga } from "../components/Estado";
import GuiaLectura from "../components/GuiaLectura";
import PageHeader from "../components/PageHeader";
import PanelModelo from "../components/PanelModelo";
import Tarjeta from "../components/Tarjeta";
import { useCarga } from "../hooks/useCarga";
import { obtenerModelo } from "../services/analisisService";
import type { Modelo } from "../types/analisis";
import {
  etiquetaCategoria,
  formatearDecimal,
  formatearEntero,
  formatearFecha,
  formatearPorcentaje,
} from "../utils/formato";
import local from "./Analisis.module.css";
import estilos from "./Pagina.module.css";

interface Objetivo {
  codigo: string;
  texto: string;
  meta: string;
  resultado: string;
  cumple: boolean;
}

function objetivos(m: Modelo): Objetivo[] {
  const ev = (t: string) => m.evaluaciones.find((e) => e.tipo_evaluacion === t);
  const canc = ev("cancelacion");
  const ns = ev("no_show");
  const oc = ev("ocupacion");
  const filas: Objetivo[] = [];
  if (canc)
    filas.push({
      codigo: "RNF-01",
      texto: "F1 de cancelación",
      meta: `≥ ${formatearDecimal(canc.valor_meta)}`,
      resultado: formatearDecimal(canc.f1_score),
      cumple: canc.cumple_meta,
    });
  if (ns)
    filas.push({
      codigo: "RNF-01",
      texto: "F1 de no-show",
      meta: `≥ ${formatearDecimal(ns.valor_meta)}`,
      resultado: formatearDecimal(ns.f1_score),
      cumple: ns.cumple_meta,
    });
  if (oc) {
    const h = oc.detalle.horizonte_referencia_dias ?? 30;
    filas.push({
      codigo: "RNF-02",
      texto: `Error de la ocupación esperada (MAPE) a ${h} días`,
      meta: `≤ ${formatearPorcentaje(oc.valor_meta, 0)}`,
      resultado: formatearPorcentaje(oc.mape),
      cumple: oc.cumple_meta,
    });
    const det = oc.detalle.riesgo_deteccion?.por_horizonte["14"]?.alerta_temprana;
    if (det) {
      const meta = m.metas.deteccion_riesgo_pct ?? 80;
      const recall = (det.recall ?? 0) * 100;
      filas.push({
        codigo: "RNF-03",
        texto: "Noches de riesgo detectadas a 14 días (alerta temprana)",
        meta: `≥ ${formatearPorcentaje(meta, 0)}`,
        resultado: formatearPorcentaje(recall, 0),
        cumple: recall >= meta,
      });
    }
  }
  return filas;
}

function Ficha({ datos }: { datos: Modelo }) {
  const v = datos.version!;
  const canc = datos.evaluaciones.find((e) => e.tipo_evaluacion === "cancelacion");
  return (
    <Tarjeta
      titulo="Versión del modelo"
      descripcion="Qué modelo generó las predicciones que se ven en el resto de la aplicación."
    >
      <div className={local.versionGrid}>
        <div>
          <span>Versión activa</span>
          <strong>{v.codigo_version}</strong>
        </div>
        <div>
          <span>Estado</span>
          <strong>{etiquetaCategoria(v.estado_aprobacion)}</strong>
        </div>
        <div>
          <span>Algoritmo</span>
          <strong>Gradient Boosting (scikit-learn)</strong>
        </div>
        <div>
          <span>Entrenado el</span>
          <strong>{formatearFecha(v.fecha_entrenamiento)}</strong>
        </div>
        <div>
          <span>Reservas usadas para aprender</span>
          <strong>
            {formatearFecha(v.periodo_entrenamiento_inicio)} a{" "}
            {formatearFecha(v.periodo_entrenamiento_fin)}
          </strong>
        </div>
        <div>
          <span>Periodo de prueba (no visto al entrenar)</span>
          <strong>
            {canc
              ? `${formatearFecha(canc.periodo_inicio)} a ${formatearFecha(canc.periodo_fin)}`
              : "—"}
          </strong>
        </div>
        <div>
          <span>Origen de los datos</span>
          <strong>Simulados</strong>
        </div>
        <div>
          <span>Reservas del periodo de prueba</span>
          <strong>{canc ? formatearEntero(canc.registros_evaluados) : "—"}</strong>
        </div>
      </div>
    </Tarjeta>
  );
}

export default function ModeloPage() {
  const { datos, cargando, error, recargar } = useCarga(obtenerModelo);

  return (
    <>
      <PageHeader
        antetitulo="Calidad de las predicciones"
        titulo="Modelo y métricas"
        descripcion="Qué modelo se está usando, qué tan bien acierta y qué límites tiene. Sirve para saber cuánto confiar en las cifras del resto de la aplicación."
      />

      {cargando && <Cargando texto="Cargando las métricas del modelo…" />}
      {error && <ErrorCarga mensaje={error} reintentar={recargar} />}
      {datos && !datos.version && (
        <ErrorCarga mensaje="Aún no hay un modelo entrenado. En la carpeta backend ejecuta: python -m scripts.entrenar_modelo" />
      )}

      {datos?.version && (
        <div className={estilos.pila}>
          <GuiaLectura>
            <p>
              El modelo estima, para cada reserva, la probabilidad de que se presente, cancele o no
              llegue (no-show), y con eso calcula la ocupación esperada de cada noche.
            </p>
            <p>
              Sus métricas se calculan con reservas que el modelo no vio al aprender. Las metas del
              proyecto aparecen junto a cada resultado, tanto si se cumplen como si no.
            </p>
          </GuiaLectura>

          <Ficha datos={datos} />

          <Tarjeta
            titulo="Metas del proyecto frente a los resultados"
            descripcion="Requisitos no funcionales del SRS que miden la calidad de las predicciones."
          >
            <div className={estilos.tablaWrap}>
              <table className={estilos.tabla}>
                <thead>
                  <tr>
                    <th>Requisito</th>
                    <th>Qué se mide</th>
                    <th className={estilos.num}>Meta</th>
                    <th className={estilos.num}>Resultado</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {objetivos(datos).map((o) => (
                    <tr key={o.texto}>
                      <td className={estilos.fuerte}>{o.codigo}</td>
                      <td>{o.texto}</td>
                      <td className={estilos.num}>{o.meta}</td>
                      <td className={`${estilos.num} ${estilos.fuerte}`}>{o.resultado}</td>
                      <td>
                        <span
                          className={`${estilos.chipMeta} ${o.cumple ? estilos.cumple : estilos.nocumple}`}
                        >
                          {o.cumple ? (
                            <CircleCheck size={13} aria-hidden />
                          ) : (
                            <TriangleAlert size={13} aria-hidden />
                          )}
                          {o.cumple ? "Cumple" : "No cumple"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Tarjeta>

          <PanelModelo datos={datos} />

          <Tarjeta
            titulo="Límites y cosas que conviene saber"
            descripcion="Para interpretar las cifras con criterio."
          >
            <ul className={local.lista}>
              <li>
                <strong>Los datos son simulados.</strong> Las cifras demuestran que el sistema
                funciona; no son el desempeño sobre las reservas reales del hotel.
              </li>
              <li>
                <strong>El F1 queda bajo la meta.</strong> Cancelar y no presentarse son eventos
                poco frecuentes, y con este tipo de datos el F1 de 0,80 no se alcanza. Las
                probabilidades sí están bien calibradas y ordenan bien el riesgo (AUC). Se propone
                revisar la meta mediante el control de cambios del proyecto (RN-09).
              </li>
              <li>
                <strong>La ocupación incluye las reservas que aún llegarán.</strong> Además de
                reservadas − cancelaciones − no-shows, se suma el “pickup” aprendido de la historia;
                sin él el error sería mucho mayor. Es un ajuste respecto del Business Case.
              </li>
              <li>
                <strong>Cuanto más lejana la fecha, más incierta.</strong> El error crece con los
                días de anticipación; por eso los gráficos muestran un margen de error.
              </li>
              <li>
                <strong>Pocas noches de riesgo.</strong> Hay muy pocas noches con ocupación muy alta
                en el periodo de prueba, así que medir cuántas se detectan es poco estable.
              </li>
              <li>
                <strong>PredicTree no decide.</strong> Muestra estimaciones y sugerencias; las
                decisiones sobre reservas, overbooking y tarifas las toma el hotel.
              </li>
            </ul>
          </Tarjeta>
        </div>
      )}
    </>
  );
}
