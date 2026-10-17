import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";

export default function NotFoundPage() {
  return (
    <>
      <PageHeader
        antetitulo="Error 404"
        titulo="Página no encontrada"
        descripcion="La dirección que buscas no existe en PredicTree."
      />
      <Link to="/dashboard" style={{ color: "var(--color-primario)", fontWeight: 600 }}>
        Volver al dashboard
      </Link>
    </>
  );
}
