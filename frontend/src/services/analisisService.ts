import type {
  Dashboard,
  DetalleNoche,
  Estado,
  Ocupacion,
  ReferenciaTarifa,
  Riesgo,
  Tarifas,
  FiltrosPredicciones,
  Modelo,
  PaginaPredicciones,
  ResumenPredicciones,
} from "../types/analisis";
import { api } from "./api";

export async function obtenerDashboard(dias = 90): Promise<Dashboard> {
  const { data } = await api.get<Dashboard>("/dashboard", { params: { dias } });
  return data;
}

export async function obtenerEstado(): Promise<Estado> {
  const { data } = await api.get<Estado>("/estado");
  return data;
}

export async function obtenerOcupacion(dias = 90): Promise<Ocupacion> {
  const { data } = await api.get<Ocupacion>("/ocupacion", { params: { dias } });
  return data;
}

export async function obtenerRiesgo(dias = 90): Promise<Riesgo> {
  const { data } = await api.get<Riesgo>("/riesgo", { params: { dias } });
  return data;
}

export async function obtenerDetalleNoche(fecha: string): Promise<DetalleNoche> {
  const { data } = await api.get<DetalleNoche>(`/noches/${fecha}`);
  return data;
}

export async function obtenerTarifas(): Promise<Tarifas> {
  const { data } = await api.get<Tarifas>("/tarifas");
  return data;
}

export async function guardarReferenciaTarifa(
  modo: "automatica" | "manual",
  tarifas: Record<string, number>,
): Promise<ReferenciaTarifa> {
  const { data } = await api.put<ReferenciaTarifa>("/tarifas/referencia", { modo, tarifas });
  return data;
}

export async function obtenerPredicciones(f: FiltrosPredicciones): Promise<PaginaPredicciones> {
  const params: Record<string, string | number> = {
    pagina: f.pagina,
    tamano: f.tamano,
    orden: f.orden,
  };
  if (f.nivel) params.nivel = f.nivel;
  if (f.canal) params.canal = f.canal;
  if (f.buscar) params.buscar = f.buscar;
  const { data } = await api.get<PaginaPredicciones>("/predicciones", { params });
  return data;
}

export async function obtenerResumenPredicciones(): Promise<ResumenPredicciones> {
  const { data } = await api.get<ResumenPredicciones>("/predicciones/resumen");
  return data;
}

export async function obtenerModelo(): Promise<Modelo> {
  const { data } = await api.get<Modelo>("/modelo");
  return data;
}
