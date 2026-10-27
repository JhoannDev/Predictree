import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  etiquetaCategoria,
  desglosarHabitaciones,
  formatearEntero,
  formatearFecha,
  formatearFechaCorta,
  formatearPorcentaje,
} from "../utils/formato";
import type { Noche, PuntoCalibracion, PuntoSerie } from "../types/analisis";
import { COLORES, TICK } from "./estilo";
import styles from "./Graficos.module.css";

const EJES = { stroke: COLORES.grilla } as const;

function Fila({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div className={styles.fila}>
      <span>{etiqueta}</span>
      <strong>{valor}</strong>
    </div>
  );
}

/* ---------------------------------------------------------------------------------------------
 * Ocupación esperada frente a la capacidad (Dashboard)
 * ------------------------------------------------------------------------------------------- */

interface OcupacionProps {
  noches: Noche[];
  umbralMedio: number;
  umbralAlto: number;
  alto?: number;
  /** Muestra la franja de incertidumbre (error esperado según los días de anticipación). */
  conBanda?: boolean;
  /** Se llama con la fecha al hacer clic en una noche del gráfico. */
  alSeleccionar?: (fecha: string) => void;
  seleccionada?: string | null;
}

export function GraficoOcupacion({
  noches,
  umbralMedio,
  umbralAlto,
  alto = 340,
  conBanda = false,
  alSeleccionar,
  seleccionada,
}: OcupacionProps) {
  const datos = noches.map((n) => ({ ...n, banda: [n.banda_inf_pct, n.banda_sup_pct] }));
  const pico = Math.max(
    ...noches.map((n) => (conBanda ? n.banda_sup_pct : n.porcentaje_ocupacion)),
  );
  // Pasar de 100 % es válido (más huéspedes que habitaciones = overbooking), pero sin exagerar el eje.
  const maximo = Math.max(100, Math.ceil(pico / 20) * 20);
  const marcas = Array.from({ length: maximo / 20 + 1 }, (_, i) => i * 20);
  return (
    <>
      <div role="img" aria-label="Ocupación esperada por noche frente a la capacidad del hotel">
        <ResponsiveContainer width="100%" height={alto}>
          <ComposedChart
            data={datos}
            margin={{ top: 10, right: 12, bottom: 0, left: -8 }}
            style={alSeleccionar ? { cursor: "pointer" } : undefined}
            onClick={(estado) => {
              const fecha = estado?.activeLabel;
              if (alSeleccionar && typeof fecha === "string") alSeleccionar(fecha);
            }}
          >
            <defs>
              <linearGradient id="relleno-ocupacion" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={COLORES.serie1} stopOpacity={0.22} />
                <stop offset="100%" stopColor={COLORES.serie1} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} stroke={COLORES.grilla} />
            <XAxis
              dataKey="fecha"
              tickFormatter={formatearFecha}
              tick={TICK}
              axisLine={EJES}
              tickLine={false}
              minTickGap={36}
            />
            <YAxis
              domain={[0, maximo]}
              ticks={marcas}
              tickFormatter={(v: number) => `${v} %`}
              tick={TICK}
              axisLine={false}
              tickLine={false}
              width={52}
            />
            <ReferenceLine y={umbralMedio} stroke={COLORES.medio} strokeDasharray="5 4" />
            <ReferenceLine y={umbralAlto} stroke={COLORES.alto} strokeDasharray="5 4" />
            <ReferenceLine y={100} stroke={COLORES.tinta} strokeOpacity={0.55} />
            <Tooltip
              content={<TooltipOcupacion />}
              cursor={{ stroke: COLORES.suave, strokeDasharray: "3 3" }}
            />
            {conBanda && (
              <Area
                type="monotone"
                dataKey="banda"
                stroke="none"
                fill={COLORES.serie1}
                fillOpacity={0.13}
                activeDot={false}
                isAnimationActive={false}
                legendType="none"
              />
            )}
            {seleccionada && (
              <ReferenceLine x={seleccionada} stroke={COLORES.tinta} strokeDasharray="2 3" />
            )}
            <Area
              type="monotone"
              dataKey="porcentaje_ocupacion"
              stroke={COLORES.serie1}
              strokeWidth={2}
              fill="url(#relleno-ocupacion)"
              dot={(p: { cx?: number; cy?: number; payload?: Noche; index?: number }) =>
                p.payload?.nivel_riesgo === "alto" && p.cx !== undefined && p.cy !== undefined ? (
                  <circle
                    key={`d-${p.index}`}
                    cx={p.cx}
                    cy={p.cy}
                    r={4}
                    fill={COLORES.alto}
                    stroke={COLORES.superficie}
                    strokeWidth={2}
                  />
                ) : (
                  <g key={`d-${p.index}`} />
                )
              }
              activeDot={{ r: 5, stroke: COLORES.superficie, strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className={styles.leyenda}>
        <span className={styles.leyendaItem}>
          <span className={styles.linea} style={{ borderColor: COLORES.serie1 }} /> Ocupación
          esperada
        </span>
        <span className={styles.leyendaItem}>
          <span className={styles.punto} style={{ background: COLORES.alto }} /> Fecha crítica
          (riesgo alto)
        </span>
        <span className={styles.leyendaItem}>
          <span
            className={`${styles.linea} ${styles.discontinua}`}
            style={{ borderColor: COLORES.medio }}
          />
          Riesgo medio desde {umbralMedio} %
        </span>
        <span className={styles.leyendaItem}>
          <span
            className={`${styles.linea} ${styles.discontinua}`}
            style={{ borderColor: COLORES.alto }}
          />
          Riesgo alto desde {umbralAlto} %
        </span>
        {conBanda && (
          <span className={styles.leyendaItem}>
            <span className={styles.franja} /> Rango probable (margen de error)
          </span>
        )}
        <span className={styles.leyendaItem}>
          <span className={styles.linea} style={{ borderColor: COLORES.tinta }} /> Capacidad (100 %)
        </span>
      </div>
    </>
  );
}

function TooltipOcupacion({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: Noche }[];
}) {
  if (!active || !payload?.length) return null;
  const n = payload[0].payload;
  const h = desglosarHabitaciones(n);
  return (
    <div className={styles.tooltip}>
      <p className={styles.tooltipTitulo}>{formatearFechaCorta(n.fecha)}</p>
      <Fila
        etiqueta="Ocupación esperada"
        valor={`${formatearPorcentaje(n.porcentaje_ocupacion)} (≈ ${h.esperadas} hab.)`}
      />
      <Fila etiqueta="Habitaciones reservadas" valor={String(h.reservadas)} />
      <Fila etiqueta="− Cancelaciones estimadas" valor={`−${h.cancelaciones}`} />
      <Fila etiqueta="− No-shows estimados" valor={`−${h.noshows}`} />
      <Fila etiqueta="+ Reservas por llegar" valor={`+${h.porLlegar}`} />
      <Fila
        etiqueta="Rango probable de ocupación"
        valor={`${formatearPorcentaje(n.banda_inf_pct, 0)} a ${formatearPorcentaje(n.banda_sup_pct, 0)}`}
      />
      <Fila etiqueta="Riesgo de overbooking" valor={etiquetaCategoria(n.nivel_riesgo)} />
    </div>
  );
}

/* ---------------------------------------------------------------------------------------------
 * Barras horizontales (por canal, importancia de variables)
 * ------------------------------------------------------------------------------------------- */

interface BarraItem {
  nombre: string;
  valor: number;
}

export function GraficoBarrasHorizontales({
  datos,
  formato = (v: number) => formatearPorcentaje(v),
  etiquetaValor = "Valor",
  maximo,
}: {
  datos: BarraItem[];
  formato?: (v: number) => string;
  etiquetaValor?: string;
  maximo?: number;
}) {
  return (
    <div role="img" aria-label={etiquetaValor}>
      <ResponsiveContainer width="100%" height={Math.max(120, datos.length * 38 + 16)}>
        <BarChart data={datos} layout="vertical" margin={{ top: 0, right: 56, bottom: 0, left: 0 }}>
          <XAxis type="number" hide domain={[0, maximo ?? "dataMax"]} />
          <YAxis
            type="category"
            dataKey="nombre"
            width={150}
            tick={{ fontSize: 12, fill: COLORES.tinta }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgb(20 71 184 / 6%)" }}
            formatter={(v) => [formato(Number(v)), etiquetaValor]}
            contentStyle={{ borderRadius: 12, border: `1px solid ${COLORES.grilla}`, fontSize: 12 }}
          />
          <Bar
            dataKey="valor"
            fill={COLORES.serie1}
            barSize={18}
            radius={[0, 4, 4, 0]}
            isAnimationActive={false}
          >
            <LabelList
              dataKey="valor"
              position="right"
              formatter={(v) => formato(Number(v))}
              style={{ fontSize: 12, fill: COLORES.tinta }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ---------------------------------------------------------------------------------------------
 * Columnas: histograma de probabilidades y MAPE por horizonte
 * ------------------------------------------------------------------------------------------- */

/** Máximo "redondo" para el eje (ej. 520 → 600) y las marcas cada tanto, para que no queden valores raros. */
function ejeRedondo(maximo: number): { tope: number; marcas: number[] } {
  if (maximo <= 0) return { tope: 1, marcas: [0, 1] };
  const bruto = maximo / 4;
  const potencia = 10 ** Math.floor(Math.log10(bruto));
  const paso = [1, 2, 2.5, 5, 10].map((m) => m * potencia).find((p) => p >= bruto) ?? bruto;
  const tope = Math.ceil(maximo / paso) * paso;
  const marcas: number[] = [];
  for (let v = 0; v <= tope + paso / 1000; v += paso) marcas.push(Math.round(v * 1e6) / 1e6);
  return { tope, marcas };
}

export function GraficoColumnas({
  datos,
  etiquetaValor,
  formatoEje = (v: number) => String(v),
  formatoValor = (v: number) => formatearEntero(v),
  meta,
  etiquetaMeta,
  alto = 240,
  colorDe,
}: {
  datos: { nombre: string; valor: number }[];
  /** Color de cada columna (por defecto, azul de marca). */
  colorDe?: (nombre: string) => string;
  etiquetaValor: string;
  formatoEje?: (v: number) => string;
  formatoValor?: (v: number) => string;
  meta?: number;
  etiquetaMeta?: string;
  alto?: number;
}) {
  const { tope, marcas } = ejeRedondo(Math.max(...datos.map((d) => d.valor), meta ?? 0));
  return (
    <div role="img" aria-label={etiquetaValor}>
      <ResponsiveContainer width="100%" height={alto}>
        <BarChart data={datos} margin={{ top: 22, right: 12, bottom: 0, left: -8 }}>
          <CartesianGrid vertical={false} stroke={COLORES.grilla} />
          <XAxis dataKey="nombre" tick={TICK} axisLine={EJES} tickLine={false} />
          <YAxis
            tick={TICK}
            axisLine={false}
            tickLine={false}
            tickFormatter={formatoEje}
            width={48}
            domain={[0, tope]}
            ticks={marcas}
            interval={0}
          />
          {meta !== undefined && (
            <ReferenceLine
              y={meta}
              stroke={COLORES.alto}
              strokeDasharray="5 4"
              label={{
                value: etiquetaMeta,
                position: "insideTopRight",
                fill: COLORES.suave,
                fontSize: 12,
              }}
            />
          )}
          <Tooltip
            cursor={{ fill: "rgb(20 71 184 / 6%)" }}
            formatter={(v) => [formatoValor(Number(v)), etiquetaValor]}
            contentStyle={{ borderRadius: 12, border: `1px solid ${COLORES.grilla}`, fontSize: 12 }}
          />
          <Bar
            dataKey="valor"
            fill={COLORES.serie1}
            barSize={24}
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          >
            {colorDe && datos.map((d) => <Cell key={d.nombre} fill={colorDe(d.nombre)} />)}
            <LabelList
              dataKey="valor"
              position="top"
              formatter={(v) => formatoValor(Number(v))}
              style={{ fontSize: 12, fill: COLORES.tinta }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ---------------------------------------------------------------------------------------------
 * Calibración: probabilidad estimada vs. frecuencia real
 * ------------------------------------------------------------------------------------------- */

export function GraficoCalibracion({ puntos }: { puntos: PuntoCalibracion[] }) {
  const datos = puntos.map((p) => ({
    estimada: p.probabilidad_media * 100,
    real: p.frecuencia_real * 100,
    casos: p.casos,
  }));
  const tope = Math.ceil(Math.max(...datos.map((d) => Math.max(d.estimada, d.real))) / 5) * 5 + 5;
  return (
    <>
      <div role="img" aria-label="Probabilidad estimada frente a frecuencia real de cancelación">
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={datos} margin={{ top: 10, right: 16, bottom: 18, left: -4 }}>
            <CartesianGrid stroke={COLORES.grilla} />
            <XAxis
              type="number"
              dataKey="estimada"
              domain={[0, tope]}
              tickFormatter={(v: number) => `${v} %`}
              tick={TICK}
              axisLine={EJES}
              tickLine={false}
              label={{
                value: "Probabilidad estimada por el modelo",
                position: "insideBottom",
                offset: -12,
                fontSize: 12,
                fill: COLORES.suave,
              }}
            />
            <YAxis
              type="number"
              domain={[0, tope]}
              tickFormatter={(v: number) => `${v} %`}
              tick={TICK}
              axisLine={false}
              tickLine={false}
              width={52}
            />
            <ReferenceLine
              segment={[
                { x: 0, y: 0 },
                { x: tope, y: tope },
              ]}
              stroke={COLORES.suave}
              strokeDasharray="5 4"
            />
            <Tooltip
              formatter={(v, nombre) => [
                formatearPorcentaje(Number(v)),
                nombre === "real" ? "Cancelaron realmente" : "Estimado",
              ]}
              contentStyle={{
                borderRadius: 12,
                border: `1px solid ${COLORES.grilla}`,
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="real"
              stroke={COLORES.serie1}
              strokeWidth={2}
              dot={{ r: 4, fill: COLORES.serie1, stroke: COLORES.superficie, strokeWidth: 2 }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className={styles.leyenda}>
        <span className={styles.leyendaItem}>
          <span className={styles.linea} style={{ borderColor: COLORES.serie1 }} /> Frecuencia real
          de cancelación
        </span>
        <span className={styles.leyendaItem}>
          <span
            className={`${styles.linea} ${styles.discontinua}`}
            style={{ borderColor: COLORES.suave }}
          />{" "}
          Calibración perfecta
        </span>
      </div>
    </>
  );
}

/* ---------------------------------------------------------------------------------------------
 * Serie de prueba: ocupación real vs. esperada
 * ------------------------------------------------------------------------------------------- */

export function GraficoBacktest({ serie }: { serie: PuntoSerie[] }) {
  return (
    <>
      <div
        role="img"
        aria-label="Ocupación real frente a la esperada por el modelo en el periodo de prueba"
      >
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={serie} margin={{ top: 10, right: 12, bottom: 0, left: -8 }}>
            <CartesianGrid vertical={false} stroke={COLORES.grilla} />
            <XAxis
              dataKey="fecha"
              tickFormatter={formatearFecha}
              tick={TICK}
              axisLine={EJES}
              tickLine={false}
              minTickGap={36}
            />
            <YAxis
              tickFormatter={(v: number) => `${v} %`}
              tick={TICK}
              axisLine={false}
              tickLine={false}
              width={52}
              domain={[0, "auto"]}
            />
            <Tooltip
              labelFormatter={(f) => formatearFechaCorta(String(f))}
              formatter={(v, nombre) => [
                formatearPorcentaje(Number(v)),
                nombre === "real_pct"
                  ? "Real"
                  : nombre === "referencia_pct"
                    ? "Referencia sin reservas"
                    : "Esperada (14 días antes)",
              ]}
              contentStyle={{
                borderRadius: 12,
                border: `1px solid ${COLORES.grilla}`,
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="referencia_pct"
              stroke={COLORES.suave}
              strokeWidth={1.5}
              strokeDasharray="5 4"
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="real_pct"
              stroke={COLORES.tinta}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="esperada_14d_pct"
              stroke={COLORES.serie1}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className={styles.leyenda}>
        <span className={styles.leyendaItem}>
          <span className={styles.linea} style={{ borderColor: COLORES.tinta }} /> Ocupación real
        </span>
        <span className={styles.leyendaItem}>
          <span className={styles.linea} style={{ borderColor: COLORES.serie1 }} /> Esperada por el
          modelo 14 días antes
        </span>
        <span className={styles.leyendaItem}>
          <span
            className={`${styles.linea} ${styles.discontinua}`}
            style={{ borderColor: COLORES.suave }}
          />{" "}
          Referencia sin reservas (solo día de la semana y calendario)
        </span>
      </div>
    </>
  );
}

/* ---------------------------------------------------------------------------------------------
 * Noches por nivel de riesgo, por mes (pantalla Riesgo de overbooking)
 * ------------------------------------------------------------------------------------------- */

export interface MesRiesgo {
  mes: string;
  bajo: number;
  medio: number;
  alto: number;
}

export function GraficoRiesgoMensual({ datos }: { datos: MesRiesgo[] }) {
  return (
    <>
      <div role="img" aria-label="Noches por nivel de riesgo en cada mes">
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={datos} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
            <CartesianGrid vertical={false} stroke={COLORES.grilla} />
            <XAxis dataKey="mes" tick={TICK} axisLine={EJES} tickLine={false} />
            <YAxis tick={TICK} axisLine={false} tickLine={false} width={44} allowDecimals={false} />
            <Tooltip
              cursor={{ fill: "rgb(20 71 184 / 6%)" }}
              formatter={(v, nombre) => [`${v} noches`, `Riesgo ${String(nombre)}`]}
              contentStyle={{
                borderRadius: 12,
                border: `1px solid ${COLORES.grilla}`,
                fontSize: 12,
              }}
            />
            <Bar dataKey="bajo" stackId="r" fill={COLORES.bajo} isAnimationActive={false} />
            <Bar dataKey="medio" stackId="r" fill={COLORES.medio} isAnimationActive={false} />
            <Bar
              dataKey="alto"
              stackId="r"
              fill={COLORES.alto}
              radius={[4, 4, 0, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className={styles.leyenda}>
        {(
          [
            ["Riesgo bajo", COLORES.bajo],
            ["Riesgo medio", COLORES.medio],
            ["Riesgo alto", COLORES.alto],
          ] as const
        ).map(([texto, color]) => (
          <span key={texto} className={styles.leyendaItem}>
            <span className={styles.cuadro} style={{ background: color }} /> {texto}
          </span>
        ))}
      </div>
    </>
  );
}
