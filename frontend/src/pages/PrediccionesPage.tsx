import EnConstruccion from "../components/EnConstruccion";
import PageHeader from "../components/PageHeader";

export default function PrediccionesPage() {
  return (
    <>
      <PageHeader
        antetitulo="Predicciones"
        titulo="Predicciones de cancelación y no-show"
        descripcion="Probabilidades por reserva y los factores que las explican."
      />
      <EnConstruccion contenido="Lista de reservas con su probabilidad de cancelación y no-show, y el detalle de los factores de cada predicción." />
    </>
  );
}
