import { useMemo, useState } from "react";
import { GraficoRiesgoMensual, type MesRiesgo } from "../charts/Graficos";
import ChipRiesgo from "../components/ChipRiesgo";
import { Cargando, ErrorCarga, SinAnalisis } from "../components/Estado";
import GuiaLectura from "../components/GuiaLectura";
import PageHeader from "../components/PageHeader";
import PanelNoche from "../components/PanelNoche";
import SelectorRango from "../components/SelectorRango";
import Tarjeta from "../components/Tarjeta";
import { useCarga } from "../hooks/useCarga";
import { obtenerRiesgo } from "../services/analisisService";
import type { NivelRiesgo } from "../types/analisis";
import {
  formatearDecimal,
  formatearEntero,
  formatearFechaCorta,
  formatearPorcentaje,
} from "../utils/formato";
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

export default function RiesgoPage() {
  const [dias, setDias] = useState(90);
  const [fecha, setFecha] = useState<string | null>(null);
  const { datos, cargando, error, recargar } = useCarga(() => obtenerRiesgo(dias), [dias]);

  const meses = useMemo<MesRiesgo[]>(() => {
    const mapa = new Map<string, MesRiesgo>();
    for (const n of datos?.noches ?? []) {
      const clave = n.fecha.slice(0, 7);
      const mes = Number(clave.slice(5)) - 1;
      const fila = mapa.get(clave) ?? { mes: MESES[mes].slice(0, 3), bajo: 0, medio: 0, alto: 0 };
      fila[n.nivel_riesgo] += 1;
      mapa.set(clave, fila);
    }
    return [...mapa.values()];
  }, [datos]);

  const aVigilar = useMemo(() => {
    if (!datos) return [];
    return datos.noches
      .filter((n) => n.nivel_riesgo !== "bajo" || n.banda_sup_pct >= datos.umbral_medio)
      .sort((a, b) => b.porcentaje_ocupacion - a.porcentaje_ocupacion)
      .slice(0, 20);
  }, [datos]);

  const total = datos?.noches.length ?? 0;
  const niveles: { nivel: NivelRiesgo; clase: string; titulo: string; texto: string }[] = datos
    ? [
        {
          nivel: "bajo",
          clase: local.nivelBajo,
          titulo: "Hay holgura",
          texto: `Se espera menos de ${datos.umbral_medio} % de ocupación. No hay riesgo de overbooking.`,
        },
        {
          nivel: "medio",
          clase: local.nivelMedio,
          titulo: "Cerca del límite",
          texto: `Entre ${datos.umbral_medio} % y menos de ${datos.umbral_alto} %. Conviene seguir las nuevas reservas y cancelaciones.`,
        },
        {
          nivel: "alto",
          clase: local.nivelAlto,
          titulo: "Fecha crítica",
          texto: `Desde ${datos.umbral_alto} %. Es posible que haya más huéspedes que habitaciones.`,
        },
      ]
    : [];

  return (
    <>
      <PageHeader
        antetitulo="Análisis de ocupación"
        titulo="Riesgo de overbooking"
        descripcion="Qué noches podrían quedar justas o superar la capacidad del hotel, según la ocupación esperada."
      />

      {cargando && !datos && <Cargando texto="Cargando el riesgo…" />}
      {error && <ErrorCarga mensaje={error} reintentar={recargar} />}
      {datos && !datos.ejecucion && <SinAnalisis />}

      {datos?.ejecucion && (
        <div className={estilos.pila}>
          <div className={local.barra}>
            <GuiaLectura>
              <p>
                El riesgo de cada noche sale de comparar la ocupación esperada con la capacidad. Es
                una alerta para mirar la noche con más atención; no es una orden ni cambia nada en
                las reservas.
              </p>
              <p>
                Como la ocupación es una estimación, también se listan las noches que, dentro del
                margen de error, podrían subir de nivel.
              </p>
            </GuiaLectura>
            <SelectorRango valor={dias} alCambiar={setDias} />
          </div>

          <div className={local.niveles}>
            {niveles.map((n) => (
              <article key={n.nivel} className={`${local.nivel} ${n.clase}`}>
                <ChipRiesgo nivel={n.nivel} />
                <p className={local.nivelNumero}>
                  {datos.resumen[n.nivel]}{" "}
                  <small style={{ fontSize: 14, fontWeight: 600 }}>
                    {datos.resumen[n.nivel] === 1 ? "noche" : "noches"} ·{" "}
                    {formatearPorcentaje((datos.resumen[n.nivel] / total) * 100, 0)}
                  </small>
                </p>
                <strong>{n.titulo}</strong>
                <p className={local.nivelTexto}>{n.texto}</p>
              </article>
            ))}
          </div>

          <div className={estilos.dosColumnas}>
            <Tarjeta
              titulo="Noches por nivel de riesgo y mes"
              descripcion="Cómo se reparte el riesgo a lo largo del periodo."
            >
              <GraficoRiesgoMensual datos={meses} />
            </Tarjeta>

            <Tarjeta
              titulo="Noches a vigilar"
              descripcion="Las de mayor ocupación esperada y las que podrían subir de nivel por el margen de error."
            >
              <div className={`${estilos.tablaWrap} ${local.scroll}`} style={{ maxHeight: 330 }}>
                <table className={estilos.tabla}>
                  <thead>
                    <tr>
                      <th>Fecha</th>
                      <th className={estilos.num}>Ocupación</th>
                      <th className={estilos.num}>Podría llegar a</th>
                      <th>Riesgo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {aVigilar.map((n) => (
                      <tr
                        key={n.fecha}
                        className={local.filaClic}
                        tabIndex={0}
                        onClick={() => setFecha(n.fecha)}
                        onKeyDown={(e) => e.key === "Enter" && setFecha(n.fecha)}
                      >
                        <td className={`${estilos.fuerte} ${estilos.nowrap}`}>
                          {formatearFechaCorta(n.fecha)}
                          {n.exceso_habitaciones > 0 && (
                            <div className={estilos.notaChica}>
                              +{formatearEntero(n.exceso_habitaciones)} hab. sobre la capacidad
                            </div>
                          )}
                        </td>
                        <td className={`${estilos.num} ${estilos.fuerte}`}>
                          {formatearPorcentaje(n.porcentaje_ocupacion)}
                        </td>
                        <td className={`${estilos.num} ${estilos.suave}`}>
                          {formatearPorcentaje(n.banda_sup_pct, 0)}
                        </td>
                        <td>
                          <ChipRiesgo nivel={n.nivel_riesgo} />
                        </td>
                      </tr>
                    ))}
                    {aVigilar.length === 0 && (
                      <tr>
                        <td colSpan={4} className={local.vacio}>
                          Ninguna noche se acerca al riesgo medio en este periodo.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <p className={estilos.notaChica} style={{ marginTop: 8 }}>
                “Podría llegar a” = ocupación esperada + margen de error (
                {formatearDecimal(
                  datos.noches.reduce((a, n) => a + n.error_esperado_pct, 0) / total,
                  1,
                )}{" "}
                % en promedio).
              </p>
            </Tarjeta>
          </div>
        </div>
      )}
      {fecha && <PanelNoche fecha={fecha} alCerrar={() => setFecha(null)} />}
    </>
  );
}
