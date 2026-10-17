import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { setUnauthorizedHandler, tokenStorage } from "../services/api";
import * as authService from "../services/authService";
import type { Usuario } from "../types/auth";
import { AuthContext } from "./authContext";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  // Si hay un token guardado, primero se verifica con la API antes de mostrar la app.
  const [cargando, setCargando] = useState(() => tokenStorage.get() !== null);

  const logout = useCallback(() => {
    tokenStorage.clear();
    setUsuario(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  useEffect(() => {
    if (!tokenStorage.get()) return;
    let activo = true;
    authService
      .obtenerPerfil()
      .then((perfil) => {
        if (activo) setUsuario(perfil);
      })
      .catch(() => {
        if (activo) tokenStorage.clear();
      })
      .finally(() => {
        if (activo) setCargando(false);
      });
    return () => {
      activo = false;
    };
  }, []);

  const login = useCallback(async (nombreUsuario: string, clave: string) => {
    const respuesta = await authService.iniciarSesion(nombreUsuario, clave);
    tokenStorage.set(respuesta.access_token);
    setUsuario(respuesta.usuario);
  }, []);

  const valor = useMemo(
    () => ({ usuario, cargando, login, logout }),
    [usuario, cargando, login, logout],
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}
