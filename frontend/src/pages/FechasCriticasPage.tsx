import EnConstruccion from "../components/EnConstruccion";
import PageHeader from "../components/PageHeader";

export default function FechasCriticasPage() {
  return (
    <>
      <PageHeader
        antetitulo="Seguimiento"
        titulo="Fechas críticas"
        descripcion="Calendario de las fechas con riesgo alto que requieren revisión."
      />
      <EnConstruccion contenido="Calendario mensual que resalta las fechas críticas y permite ver el detalle de cada una." />
    </>
  );
}
