import EnConstruccion from "../components/EnConstruccion";
import PageHeader from "../components/PageHeader";

export default function DashboardPage() {
  return (
    <>
      <PageHeader
        antetitulo="Panel de control"
        titulo="Dashboard"
        descripcion="Resumen de predicciones y riesgo por fecha."
      />
      <EnConstruccion contenido="Indicadores de ocupación esperada, cancelación y no-show, gráfico de ocupación esperada frente a la capacidad y fechas con riesgo." />
    </>
  );
}
