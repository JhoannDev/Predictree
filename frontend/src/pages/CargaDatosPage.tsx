import EnConstruccion from "../components/EnConstruccion";
import PageHeader from "../components/PageHeader";

export default function CargaDatosPage() {
  return (
    <>
      <PageHeader
        antetitulo="Ingreso de información"
        titulo="Carga de datos"
        descripcion="Selecciona el archivo de reservas y valida sus registros antes del análisis."
      />
      <EnConstruccion contenido="Selección del archivo de reservas, validación de cada registro y resumen de observaciones por lote." />
    </>
  );
}
