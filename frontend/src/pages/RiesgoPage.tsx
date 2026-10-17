import EnConstruccion from "../components/EnConstruccion";
import PageHeader from "../components/PageHeader";

export default function RiesgoPage() {
  return (
    <>
      <PageHeader
        antetitulo="Análisis de ocupación"
        titulo="Riesgo de overbooking"
        descripcion="Clasificación del riesgo e identificación de fechas críticas."
      />
      <EnConstruccion contenido="Resumen de fechas por nivel de riesgo (bajo, medio, alto), tabla con filtro por nivel y alerta de fechas críticas." />
    </>
  );
}
