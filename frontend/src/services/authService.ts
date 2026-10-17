import type { RespuestaLogin, Usuario } from "../types/auth";
import { api } from "./api";

export async function iniciarSesion(nombreUsuario: string, clave: string): Promise<RespuestaLogin> {
  const { data } = await api.post<RespuestaLogin>("/auth/login", {
    nombre_usuario: nombreUsuario,
    clave,
  });
  return data;
}

export async function obtenerPerfil(): Promise<Usuario> {
  const { data } = await api.get<Usuario>("/auth/me");
  return data;
}
