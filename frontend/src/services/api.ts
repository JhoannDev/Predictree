import axios from "axios";

const CLAVE_TOKEN = "predictree.token";

/** Guarda el token de sesión en el navegador. */
export const tokenStorage = {
  get: () => localStorage.getItem(CLAVE_TOKEN),
  set: (token: string) => localStorage.setItem(CLAVE_TOKEN, token),
  clear: () => localStorage.removeItem(CLAVE_TOKEN),
};

/** Cliente HTTP para hablar con la API de PredicTree. */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 15000,
});

// Agrega el token a cada solicitud.
api.interceptors.request.use((config) => {
  const token = tokenStorage.get();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Si la API responde 401 (sesión vencida), se cierra la sesión.
let alNoAutorizado: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null) {
  alNoAutorizado = handler;
}

api.interceptors.response.use(
  (respuesta) => respuesta,
  (error) => {
    const esLogin = error?.config?.url?.includes("/auth/login");
    if (axios.isAxiosError(error) && error.response?.status === 401 && !esLogin) {
      alNoAutorizado?.();
    }
    return Promise.reject(error);
  },
);

/** Convierte un error de la API en un mensaje entendible para el usuario. */
export function mensajeDeError(
  error: unknown,
  porDefecto = "Ocurrió un error inesperado.",
): string {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      return "No se pudo conectar con la API. Verifica que el backend esté en ejecución.";
    }
    const detalle = error.response.data?.detail;
    if (typeof detalle === "string") {
      return detalle;
    }
  }
  return porDefecto;
}
