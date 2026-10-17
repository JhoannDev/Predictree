import { createContext } from "react";
import type { Usuario } from "../types/auth";

export interface AuthContextValue {
  usuario: Usuario | null;
  /** true mientras se verifica una sesión guardada al abrir la página. */
  cargando: boolean;
  login: (nombreUsuario: string, clave: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
