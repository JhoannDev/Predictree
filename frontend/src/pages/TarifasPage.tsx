import { ArrowDownRight, ArrowUpRight, CircleCheck, Equal, Tag, TrendingUp } from "lucide-react";
import { useState } from "react";
import ChipRiesgo from "../components/ChipRiesgo";
import { Cargando, ErrorCarga, SinAnalisis } from "../components/Estado";
import GuiaLectura from "../components/GuiaLectura";
import KpiCard from "../components/KpiCard";
import PageHeader from "../components/PageHeader";
import PanelNoche from "../components/PanelNoche";
import Tarjeta from "../components/Tarjeta";
import { useCarga } from "../hooks/useCarga";
import { mensajeDeError } from "../services/api";
import { guardarReferenciaTarifa, obtenerTarifas } from "../services/analisisService";
import type { Noche, NivelRiesgo, ReferenciaTarifa } from "../types/analisis";
import {
  formatearDecimal,
  formatearFechaCorta,
  formatearPorcentaje,
  formatearSoles,
} from "../utils/formato";
import local from "./Analisis.module.css";
import estilos from "./Pagina.module.css";

const TAMANO = 15;

type Filtro = NivelRiesgo | "" | "atencion";

const TIPO = {
  incrementar: { texto: "Subir tarifa", icono: ArrowUpRight, clase: local.sube },
  mantener: { texto: "Mantener", icono: Equal, clase: "" },
  promocion: { texto: "Evaluar promoción", icono: ArrowDownRight, clase: "" },
} as const;

function EditorReferencia({
  referencia,
  alGuardar,
}: {
  referencia: ReferenciaTarifa;
  alGuardar: () => void;
}) {
  const [modo, setModo] = useState(referencia.modo);
  const [valores, setValores] = useState<Record<string, string>>(
    Object.fromEntries(
      referencia.tipos.map((t) => [
        t.codigo,
        String(t.referencia ?? Math.round(t.promedio_reservas ?? t.tarifa_catalogo)),
      ]),
    ),
  );
  const [estado, setEstado] = useState<"idle" | "guardando" | "ok" | "error">("idle");
  const [mensaje, setMensaje] = useState("");

  async function guardar() {
    setEstado("guardando");
    try {
      const tarifas: Record<string, number> = {};
      if (modo === "manual") {
        for (const t of referencia.tipos) {
          const v = Number(valores[t.codigo].replace(",", "."));
          if (!Number.isFinite(v) || v <= 0)
            throw new Error(`Escribe una tarifa válida para ${t.nombre}.`);
          tarifas[t.codigo] = v;
        }
      }
      await guardarReferenciaTarifa(modo, tarifas);
      setEstado("ok");
      alGuardar();
    } catch (e) {
      setEstado("error");
      setMensaje(e instanceof Error && !("response" in e) ? e.message : mensajeDeError(e));
    }
  }

  return (
    <Tarjeta
      titulo="Tarifa de referencia"
      descripcion="Es la base sobre la que se calcula la tarifa sugerida. Revenue Management puede fijarla por tipo de habitación."
    >
      <div className={estilos.pila}>
        <div className={local.modos} role="radiogroup" aria-label="Cómo se calcula la referencia">
          <label className={`${local.modo} ${modo === "automatica" ? local.modoActivo : ""}`}>
            <input
              type="radio"
              name="modo"
              checked={modo === "automatica"}
              onChange={() => setModo("automatica")}
            />
            <span>
              <strong>Automática</strong>
              Promedio de lo que ya está reservado para cada noche.
            </span>
          </label>
          <label className={`${local.modo} ${modo === "manual" ? local.modoActivo : ""}`}>
            <input
              type="radio"
              name="modo"
              checked={modo === "manual"}
              onChange={() => setModo("manual")}
            />
            <span>
              <strong>Definida por Revenue Management</strong>
              Tú escribes la tarifa base de cada tipo de habitación.
            </span>
          </label>
        </div>

        {modo === "manual" && (
          <div className={local.refGrid}>
            {referencia.tipos.map((t) => (
              <label key={t.codigo} className={local.campoTarifa}>
                {t.nombre}
                <span className={local.entrada}>
                  <span>S/</span>
                  <input
                    inputMode="decimal"
                    value={valores[t.codigo]}
                    onChange={(e) => setValores((v) => ({ ...v, [t.codigo]: e.target.value }))}
                  />
                </span>
                <small>
                  Catálogo {formatearSoles(t.tarifa_catalogo)}
                  {t.promedio_reservas !== null &&
                    ` · reservado ${formatearSoles(t.promedio_reservas)}`}
                </small>
              </label>
            ))}
          </div>
        )}

        <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
          <button
            type="button"
            className={local.botonPrimario}
            onClick={guardar}
            disabled={estado === "guardando"}
          >
            {estado === "guardando" ? "Guardando…" : "Guardar y recalcular sugerencias"}
          </button>
          {estado === "ok" && (
            <span className={local.mensajeOk}>
              <CircleCheck size={15} aria-hidden /> Sugerencias recalculadas.
            </span>
          )}
          {estado === "error" && <span className={local.mensajeError}>{mensaje}</span>}
        </div>
        <p className={estilos.notaChica}>
          Guardar solo recalcula las sugerencias que ves aquí. PredicTree no modifica ninguna tarifa
          del hotel.
        </p>
      </div>
    </Tarjeta>
  );
}

export default function TarifasPage() {
  const [nivel, setNivel] = useState<Filtro>("atencion");
  const [pagina, setPagina] = useState(1);
  const [fecha, setFecha] = useState<string | null>(null);
  const { datos, cargando, error, recargar } = useCarga(obtenerTarifas);

  const todas: Noche[] = datos?.noches ?? [];
  const filtradas = todas.filter((n) =>
    nivel === ""
      ? true
      : nivel === "atencion"
        ? n.nivel_riesgo !== "bajo"
        : n.nivel_riesgo === nivel,
  );
  const paginas = Math.max(1, Math.ceil(filtradas.length / TAMANO));
  const visibles = filtradas.slice((pagina - 1) * TAMANO, pagina * TAMANO);
  const cuenta = (tipo: string) => todas.filter((n) => n.tipo_sugerencia === tipo).length;

  return (
    <>
      <PageHeader
        antetitulo="Seguimiento"
        titulo="Sugerencias de tarifa"
        descripcion="Para cada noche, un ajuste de tarifa orientativo según su nivel de riesgo. La decisión final es del hotel."
      />

      {cargando && !datos && <Cargando texto="Cargando las sugerencias…" />}
      {error && <ErrorCarga mensaje={error} reintentar={recargar} />}
      {datos && !datos.ejecucion && <SinAnalisis />}

      {datos?.ejecucion && (
        <div className={estilos.pila}>
          <GuiaLectura>
            <p>
              <strong>Tarifa sugerida = tarifa de referencia × (1 + ajuste).</strong> El ajuste
              depende del riesgo: en riesgo alto se sugiere subir entre 5 % y 8 %, en riesgo medio
              mantener, y en riesgo bajo evaluar una promoción de 3 %.
            </p>
            <p>
              Son sugerencias informativas: no cambian ninguna tarifa ni reserva. Haz clic en una
              fila para ver por qué esa noche tiene ese nivel.
            </p>
          </GuiaLectura>

          <div className={estilos.kpis} style={{ marginBottom: 0 }}>
            <KpiCard
              etiqueta="Fechas críticas con sugerencia"
              valor={`${datos.con_sugerencia} de ${datos.fechas_criticas}`}
              ayuda={`Cobertura ${formatearPorcentaje(datos.cobertura_pct, 0)}`}
              icono={CircleCheck}
              tono="verde"
            />
            <KpiCard
              etiqueta="Noches con sugerencia de subir"
              valor={String(cuenta("incrementar"))}
              ayuda="Riesgo alto: ajuste de +5 % a +8 %"
              icono={TrendingUp}
              tono="rojo"
            />
            <KpiCard
              etiqueta="Noches para mantener"
              valor={String(cuenta("mantener"))}
              ayuda="Riesgo medio: sin cambio"
              icono={Equal}
              tono="ambar"
            />
            <KpiCard
              etiqueta="Noches para evaluar promoción"
              valor={String(cuenta("promocion"))}
              ayuda="Riesgo bajo: −3 % orientativo"
              icono={Tag}
            />
          </div>

          {datos.referencia && (
            <EditorReferencia
              key={`${datos.referencia.modo}-${datos.referencia.tipos.map((t) => t.referencia).join()}`}
              referencia={datos.referencia}
              alGuardar={recargar}
            />
          )}

          <Tarjeta
            titulo="Sugerencia por fecha"
            descripcion={`Modo de referencia: ${datos.referencia?.modo === "manual" ? "definida por Revenue Management" : "automática"}.`}
            acciones={
              <div className={local.filtros} role="group" aria-label="Filtrar por riesgo">
                {(
                  [
                    ["atencion", "Requieren atención"],
                    ["", "Todas"],
                    ["alto", "Riesgo alto"],
                    ["medio", "Riesgo medio"],
                    ["bajo", "Riesgo bajo"],
                  ] as [Filtro, string][]
                ).map(([valor, texto]) => (
                  <button
                    key={valor}
                    type="button"
                    aria-pressed={nivel === valor}
                    className={`${local.ficha} ${nivel === valor ? local.fichaActiva : ""}`}
                    onClick={() => {
                      setNivel(valor);
                      setPagina(1);
                    }}
                  >
                    {texto}
                  </button>
                ))}
              </div>
            }
          >
            <div className={estilos.tablaWrap}>
              <table className={estilos.tabla}>
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th className={estilos.num}>Ocupación esperada</th>
                    <th>Riesgo</th>
                    <th className={estilos.num}>Tarifa de referencia</th>
                    <th>Sugerencia</th>
                    <th className={estilos.num}>Ajuste</th>
                    <th className={estilos.num}>Tarifa sugerida</th>
                    <th>Justificación</th>
                  </tr>
                </thead>
                <tbody>
                  {visibles.map((n) => {
                    const t = n.tipo_sugerencia ? TIPO[n.tipo_sugerencia] : null;
                    return (
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
                        <td className={estilos.num}>
                          {formatearPorcentaje(n.porcentaje_ocupacion)}
                        </td>
                        <td>
                          <ChipRiesgo nivel={n.nivel_riesgo} />
                        </td>
                        <td className={estilos.num}>{formatearSoles(n.tarifa_referencia)}</td>
                        <td>
                          {t && (
                            <span className={`${local.sugerenciaTipo} ${t.clase}`}>
                              <t.icono size={14} aria-hidden /> {t.texto}
                            </span>
                          )}
                        </td>
                        <td className={estilos.num}>
                          {n.ajuste_recomendado !== null &&
                            (n.ajuste_recomendado === 0
                              ? "Sin cambio"
                              : `${n.ajuste_recomendado > 0 ? "+" : ""}${formatearDecimal(n.ajuste_recomendado, 1)} %`)}
                        </td>
                        <td className={`${estilos.num} ${estilos.fuerte}`}>
                          {formatearSoles(n.tarifa_sugerida)}
                        </td>
                        <td className={estilos.suave} style={{ minWidth: 220 }}>
                          {n.justificacion}
                        </td>
                      </tr>
                    );
                  })}
                  {visibles.length === 0 && (
                    <tr>
                      <td colSpan={8} className={local.vacio}>
                        No hay noches con ese filtro.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className={estilos.paginacion}>
              <span>
                {filtradas.length} noches · página {pagina} de {paginas}
              </span>
              <div>
                <button
                  type="button"
                  className={estilos.boton}
                  disabled={pagina <= 1}
                  onClick={() => setPagina((p) => p - 1)}
                >
                  Anterior
                </button>{" "}
                <button
                  type="button"
                  className={estilos.boton}
                  disabled={pagina >= paginas}
                  onClick={() => setPagina((p) => p + 1)}
                >
                  Siguiente
                </button>
              </div>
            </div>
          </Tarjeta>
        </div>
      )}
      {fecha && <PanelNoche fecha={fecha} alCerrar={() => setFecha(null)} />}
    </>
  );
}
