/** "Usuario Demo" -> "UD" */
export function iniciales(nombre: string | undefined): string {
  if (!nombre) return "?";
  return nombre
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((parte) => parte[0]?.toUpperCase() ?? "")
    .join("");
}

/** "revenue_management" -> "Revenue management" */
export function formatearRol(rol: string | undefined): string {
  if (!rol) return "";
  const texto = rol.replaceAll("_", " ");
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}
