import EnConstruccion from "../components/EnConstruccion";
import PageHeader from "../components/PageHeader";

export default function OcupacionPage() {
  return (
    <>
      <PageHeader
        antetitulo="Análisis de ocupación"
        titulo="Ocupación esperada"
        descripcion="Habitaciones que se estima ocupar por fecha frente a la capacidad del hotel."
      />
      <EnConstruccion contenido="Gráfico y tabla por fecha de la ocupación esperada, considerando las probabilidades de cancelación y no-show." />
    </>
  );
}
