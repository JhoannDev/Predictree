import { CircleCheck, TriangleAlert } from "lucide-react";
import {
  GraficoBacktest,
  GraficoBarrasHorizontales,
  GraficoCalibracion,
  GraficoColumnas,
} from "../charts/Graficos";
import estilos from "../pages/Pagina.module.css";
import type { Evaluacion, Modelo } from "../types/analisis";
import {
  formatearDecimal,
  formatearEntero,
  formatearFecha,
  formatearPorcentaje,
} from "../utils/formato";
import Tarjeta from "./Tarjeta";

function ChipMeta({ cumple }: { cumple: boolean }) {
  return (
    <span className={`${estilos.chipMeta} ${cumple ? estilos.cumple : estilos.nocumple}`}>
      {cumple ? <CircleCheck size={13} aria-hidden /> : <TriangleAlert size={13} aria-hidden />}
      {cumple ? "Cumple la meta" : "Bajo la meta"}
    </span>
  );
}

const FILAS: {
  clave: keyof NonNullable<Evaluacion["detalle"]["metricas"]>;
  nombre: string;
  ayuda: string;
  pct?: boolean;
}[] = [
  { clave: "f1", nombre: "F1", ayuda: "Equilibrio entre precisión y recall (0 a 1)" },
  {
    clave: "precision",
    nombre: "Precisión",
    ayuda: "De las reservas que el modelo marca, cuántas realmente ocurren",
    pct: true,
  },
  {
    clave: "recall",
    nombre: "Recall (sensibilidad)",
    ayuda: "De las que ocurren, cuántas detecta el modelo",
    pct: true,
  },
  {
    clave: "accuracy",
    nombre: "Exactitud",
    ayuda: "Porcentaje de aciertos sobre todas las reservas",
    pct: true,
  },
  {
    clave: "auc_roc",
    nombre: "AUC-ROC",
    ayuda: "Qué tan bien ordena las reservas de menor a mayor riesgo (0,5 = azar; 1 = perfecto)",
  },
  {
    clave: "auc_pr",
    nombre: "AUC-PR",
    ayuda: "Calidad del ranking cuando el evento es poco frecuente",
  },
  {
    clave: "brier",
    nombre: "Error Brier",
    ayuda: "Error de las probabilidades (más bajo es mejor)",
  },
  {
    clave: "tasa_real",
    nombre: "Frecuencia real",
    ayuda: "Porcentaje de reservas que realmente ocurrió",
    pct: true,
  },
  {
    clave: "tasa_predicha_media",
    nombre: "Probabilidad media estimada",
    ayuda: "Debe ser cercana a la frecuencia real",
    pct: true,
  },
];

export default function PanelModelo({ datos }: { datos: Modelo }) {
  const ev = (tipo: string) => datos.evaluaciones.find((e) => e.tipo_evaluacion === tipo);
  const canc = ev("cancelacion");
  const ns = ev("no_show");
  const oc = ev("ocupacion");
  const mapes = oc?.detalle.mape_por_horizonte ?? {};
  const horizontes = Object.keys(mapes).sort((a, b) => Number(a) - Number(b));
  const det = oc?.detalle.riesgo_deteccion;

  return (
    <div className={estilos.pila}>
      <div className={estilos.aviso}>
        <p>
          <strong>Cómo leer estas métricas.</strong> Se calculan con llegadas del{" "}
          {canc
            ? `${formatearFecha(canc.periodo_inicio)} al ${formatearFecha(canc.periodo_fin)}`
            : "periodo de prueba"}
          , que el modelo no vio al entrenar. Solo se cancela el{" "}
          {formatearPorcentaje((canc?.detalle.metricas?.tasa_real ?? 0) * 100, 0)} de las reservas
          vigentes y apenas el{" "}
          {formatearPorcentaje((ns?.detalle.metricas?.tasa_real ?? 0) * 100, 0)} no se presenta; con
          eventos tan poco frecuentes el F1 es naturalmente bajo aunque las probabilidades sean
          útiles. Por eso se muestran también el AUC, la calibración y el error de la ocupación, que
          es el objetivo del negocio.
        </p>
        <p>
          <strong>Qué es la meta de F1 (0,80 para cancelación y 0,75 para no-show).</strong> Son los
          objetivos del documento de requisitos del proyecto. El F1 junta dos cosas: de las reservas
          que el modelo marca como riesgosas, cuántas de verdad ocurren (precisión:{" "}
          {formatearPorcentaje((canc?.detalle.metricas?.precision ?? 0) * 100, 0)} en cancelación y{" "}
          {formatearPorcentaje((ns?.detalle.metricas?.precision ?? 0) * 100, 0)} en no-show), y de
          las que de verdad ocurren, cuántas logra marcar (recall:{" "}
          {formatearPorcentaje((canc?.detalle.metricas?.recall ?? 0) * 100, 0)} y{" "}
          {formatearPorcentaje((ns?.detalle.metricas?.recall ?? 0) * 100, 0)}). Para llegar a 0,80
          habría que acertar en ambas a la vez. No se cumple porque son eventos poco frecuentes y,
          en estos datos, las reservas que cancelan o no llegan se parecen mucho a las que sí se
          presentan. Aun así las probabilidades son confiables: la calibración muestra que lo que el
          modelo estima coincide con lo que realmente pasa.
        </p>
        <p>
          Los datos son simulados: estas cifras demuestran el funcionamiento del sistema, no el
          desempeño sobre datos reales del hotel.
        </p>
      </div>

      <div className={estilos.dosColumnas}>
        <Tarjeta
          titulo="Cancelación y no-show en detalle"
          descripcion="Periodo de prueba, todas las fotos de reservas vigentes."
        >
          <div className={estilos.tablaWrap}>
            <table className={estilos.tabla}>
              <thead>
                <tr>
                  <th>Métrica</th>
                  <th className={estilos.num}>Cancelación</th>
                  <th className={estilos.num}>No-show</th>
                </tr>
              </thead>
              <tbody>
                {FILAS.map((f) => {
                  const a = canc?.detalle.metricas?.[f.clave];
                  const b = ns?.detalle.metricas?.[f.clave];
                  const fmt = (v: number | null | undefined) =>
                    v === null || v === undefined
                      ? "—"
                      : f.pct
                        ? formatearPorcentaje(v * 100)
                        : formatearDecimal(v, f.clave === "brier" ? 3 : 2);
                  return (
                    <tr key={f.clave} title={f.ayuda}>
                      <td>
                        <span className={estilos.fuerte}>{f.nombre}</span>
                        <div className={estilos.notaChica}>{f.ayuda}</div>
                      </td>
                      <td className={estilos.num}>{fmt(a)}</td>
                      <td className={estilos.num}>{fmt(b)}</td>
                    </tr>
                  );
                })}
                <tr>
                  <td className={estilos.fuerte}>Meta de F1</td>
                  <td className={estilos.num}>
                    {formatearDecimal(canc?.valor_meta)} <ChipMeta cumple={!!canc?.cumple_meta} />
                  </td>
                  <td className={estilos.num}>
                    {formatearDecimal(ns?.valor_meta)} <ChipMeta cumple={!!ns?.cumple_meta} />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Tarjeta>

        <Tarjeta
          titulo="Error de la ocupación esperada"
          descripcion="MAPE según los días de anticipación con que se hace la predicción."
        >
          <GraficoColumnas
            datos={horizontes.map((h) => ({
              nombre: `${h} días`,
              valor: mapes[h].mape_con_pickup,
            }))}
            etiquetaValor="MAPE"
            formatoEje={(v) => `${v} %`}
            formatoValor={(v) => formatearPorcentaje(v)}
            meta={oc?.valor_meta}
            etiquetaMeta={`Meta ${oc?.valor_meta ?? 15} %`}
          />
          <div className={estilos.tablaWrap} style={{ marginTop: 10 }}>
            <table className={estilos.tabla}>
              <thead>
                <tr>
                  <th>Anticipación</th>
                  <th className={estilos.num}>Con el modelo</th>
                  <th className={estilos.num}>Solo reservas</th>
                  <th className={estilos.num}>Solo calendario</th>
                </tr>
              </thead>
              <tbody>
                {horizontes.map((h) => (
                  <tr key={h}>
                    <td>{h} días</td>
                    <td className={`${estilos.num} ${estilos.fuerte}`}>
                      {formatearPorcentaje(mapes[h].mape_con_pickup)}
                    </td>
                    <td className={`${estilos.num} ${estilos.suave}`}>
                      {formatearPorcentaje(mapes[h].mape_sin_pickup)}
                    </td>
                    <td className={`${estilos.num} ${estilos.suave}`}>
                      {formatearPorcentaje(mapes[h].mape_referencia)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className={estilos.notaChica} style={{ marginTop: 8 }}>
            "Solo reservas" cuenta lo ya reservado menos cancelaciones y no-shows estimados, sin
            sumar las reservas que aún llegarán. La referencia usa únicamente el día de la semana y
            el calendario. A mayor anticipación el modelo aporta menos sobre la referencia: la
            incertidumbre crece.
          </p>
        </Tarjeta>
      </div>

      <div className={estilos.dosColumnas}>
        <Tarjeta
          titulo="¿Son confiables las probabilidades?"
          descripcion="Si el modelo dice 20 %, ¿cancela de verdad 1 de cada 5? Cuanto más cerca de la diagonal, mejor."
        >
          {canc?.detalle.calibracion && <GraficoCalibracion puntos={canc.detalle.calibracion} />}
        </Tarjeta>

        <Tarjeta
          titulo="Qué variables pesan más"
          descripcion="Importancia relativa en el modelo (permutación)."
        >
          <GraficoBarrasHorizontales
            datos={datos.importancia_variables
              .slice(0, 8)
              .map((v) => ({ nombre: v.nombre, valor: v.importancia_pct }))}
            etiquetaValor="Importancia"
            formato={(v) => formatearPorcentaje(v, 0)}
          />
        </Tarjeta>
      </div>

      {det && (
        <Tarjeta
          titulo="¿Detecta las noches de riesgo?"
          descripcion={`En el periodo de prueba hubo ${det.noches_riesgo_reales} noches que terminaron con ${det.umbral_pct} % de ocupación o más (de ${det.noches_evaluadas}). Aquí se ve cuántas había anticipado el modelo.`}
        >
          <div className={estilos.tablaWrap}>
            <table className={estilos.tabla}>
              <thead>
                <tr>
                  <th>Anticipación</th>
                  <th>Aviso</th>
                  <th className={estilos.num}>Noches avisadas</th>
                  <th className={estilos.num}>Acertó</th>
                  <th className={estilos.num}>Detectó (recall)</th>
                  <th className={estilos.num}>Precisión</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(det.por_horizonte).flatMap(([h, v]) =>
                  (
                    [
                      ["Al umbral", v.al_umbral],
                      ["Alerta temprana", v.alerta_temprana],
                    ] as const
                  ).map(([nombre, x]) => (
                    <tr key={`${h}-${nombre}`}>
                      <td>{h} días</td>
                      <td>
                        {nombre} <span className={estilos.suave}>(desde {x.umbral_pct} %)</span>
                      </td>
                      <td className={estilos.num}>{x.noches_alertadas}</td>
                      <td className={estilos.num}>
                        {x.aciertos} de {det.noches_riesgo_reales}
                      </td>
                      <td className={`${estilos.num} ${estilos.fuerte}`}>
                        {formatearPorcentaje((x.recall ?? 0) * 100, 0)}
                      </td>
                      <td className={estilos.num}>
                        {formatearPorcentaje((x.precision ?? 0) * 100, 0)}
                      </td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
          <p className={estilos.notaChica} style={{ marginTop: 8 }}>
            “Al umbral” avisa cuando la ocupación esperada llega al {det.umbral_pct} %. “Alerta
            temprana” avisa 5 puntos antes. La meta del proyecto es detectar al menos{" "}
            {formatearPorcentaje(datos.metas.deteccion_riesgo_pct ?? 80, 0)} de estas noches; con
            tan pocas noches de riesgo en el periodo de prueba, la cifra varía mucho. Lo razonable
            es usar la alerta temprana y revisar cada fecha con su margen de error.
          </p>
        </Tarjeta>
      )}

      {oc?.detalle.serie && (
        <Tarjeta
          titulo="Ocupación real frente a la esperada"
          descripcion={`Cada noche del periodo de prueba, estimada 14 días antes (${formatearEntero(oc.registros_evaluados)} noches).`}
        >
          <GraficoBacktest serie={oc.detalle.serie} />
        </Tarjeta>
      )}
    </div>
  );
}
