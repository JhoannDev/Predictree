import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./auth/ProtectedRoute";
import MainLayout from "./layouts/MainLayout";
import CargaDatosPage from "./pages/CargaDatosPage";
import DashboardPage from "./pages/DashboardPage";
import FechasCriticasPage from "./pages/FechasCriticasPage";
import LoginPage from "./pages/LoginPage";
import ModeloPage from "./pages/ModeloPage";
import NotFoundPage from "./pages/NotFoundPage";
import OcupacionPage from "./pages/OcupacionPage";
import PrediccionesPage from "./pages/PrediccionesPage";
import ReportesPage from "./pages/ReportesPage";
import RiesgoPage from "./pages/RiesgoPage";
import TarifasPage from "./pages/TarifasPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Todo lo que está aquí dentro exige sesión iniciada */}
      <Route element={<ProtectedRoute />}>
        <Route element={<MainLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/carga-datos" element={<CargaDatosPage />} />
          <Route path="/predicciones" element={<PrediccionesPage />} />
          <Route path="/ocupacion" element={<OcupacionPage />} />
          <Route path="/riesgo" element={<RiesgoPage />} />
          <Route path="/fechas-criticas" element={<FechasCriticasPage />} />
          <Route path="/tarifas" element={<TarifasPage />} />
          <Route path="/modelo" element={<ModeloPage />} />
          <Route path="/reportes" element={<ReportesPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
