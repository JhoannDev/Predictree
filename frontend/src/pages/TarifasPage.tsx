import EnConstruccion from "../components/EnConstruccion";
import PageHeader from "../components/PageHeader";

export default function TarifasPage() {
  return (
    <>
      <PageHeader
        antetitulo="Apoyo a la decisión"
        titulo="Sugerencias de tarifa"
        descripcion="Sugerencias informativas según el nivel de riesgo; no modifican las tarifas."
      />
      <EnConstruccion contenido="Sugerencia informativa por fecha según el nivel de riesgo y la regla aplicada. La decisión final es siempre de Revenue Management." />
    </>
  );
}
