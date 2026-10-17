import EnConstruccion from "../components/EnConstruccion";
import PageHeader from "../components/PageHeader";

export default function ReportesPage() {
  return (
    <>
      <PageHeader
        antetitulo="Resultados"
        titulo="Reportes"
        descripcion="Consulta y exportación de los reportes R-01 a R-04."
      />
      <EnConstruccion contenido="Reportes de ocupación y riesgo, fechas críticas y sugerencias, desempeño del modelo y calidad de datos, con exportación a PDF y Excel." />
    </>
  );
}
