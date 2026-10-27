/** Colores de los gráficos: salen de tokens.css (mismos valores). */
export const COLORES = {
  serie1: "#1447b8", // azul de marca
  serie2: "#eb6834", // naranja (segunda serie)
  tinta: "#0f1f3d",
  suave: "#5c6b86",
  grilla: "#e3e9f4",
  superficie: "#ffffff",
  bajo: "#16a05b",
  medio: "#f59e0b",
  alto: "#dc2638",
} as const;

export const TICK = { fontSize: 12, fill: COLORES.suave } as const;
