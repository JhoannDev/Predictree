import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./useAuth";

/** Solo deja pasar a usuarios con sesión iniciada; al resto los envía al login. */
export default function ProtectedRoute() {
  const { usuario, cargando } = useAuth();
  const location = useLocation();

  if (cargando) {
    return <div className="pantalla-carga">Verificando sesión…</div>;
  }
  if (!usuario) {
    return <Navigate to="/login" replace state={{ desde: location.pathname }} />;
  }
  return <Outlet />;
}
