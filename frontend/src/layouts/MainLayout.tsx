import { ChevronRight, Database, LogOut } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import AvisoFecha from "../components/AvisoFecha";
import Logo from "../components/Logo";
import { gruposNavegacion, navegacion } from "../config/navigation";
import { useCarga } from "../hooks/useCarga";
import { obtenerEstado } from "../services/analisisService";
import { formatearFecha, formatearRol, iniciales } from "../utils/formato";
import styles from "./MainLayout.module.css";

/** Estructura común de las pantallas internas: menú lateral + barra superior + contenido. */
export default function MainLayout() {
  const { usuario, logout } = useAuth();
  const { pathname } = useLocation();
  const { datos: estado } = useCarga(obtenerEstado);
  const actual = navegacion.find((item) => pathname.startsWith(item.ruta));

  return (
    <div className={styles.contenedor}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <Logo variante="claro" />
        </div>

        <nav className={styles.menu} aria-label="Menú principal">
          {gruposNavegacion.map((grupo) => (
            <div key={grupo} className={styles.grupo}>
              <p className={styles.grupoTitulo}>{grupo}</p>
              {navegacion
                .filter((item) => item.grupo === grupo)
                .map(({ ruta, etiqueta, icono: Icono }) => (
                  <NavLink
                    key={ruta}
                    to={ruta}
                    className={({ isActive }) =>
                      isActive ? `${styles.enlace} ${styles.enlaceActivo}` : styles.enlace
                    }
                  >
                    <Icono size={18} aria-hidden />
                    <span>{etiqueta}</span>
                  </NavLink>
                ))}
            </div>
          ))}
        </nav>

        <p className={styles.pie}>
          DoubleTree by Hilton
          <br />
          Lima Miraflores
        </p>
      </aside>

      <div className={styles.principal}>
        <header className={styles.topbar}>
          <nav className={styles.migas} aria-label="Ubicación">
            <span>{actual?.grupo ?? "General"}</span>
            <ChevronRight size={14} aria-hidden />
            <strong>{actual?.etiqueta ?? "Página no encontrada"}</strong>
          </nav>

          {estado?.fecha_corte && (
            <p
              className={styles.estado}
              title={
                estado.datos_simulados
                  ? `Datos de demostración. Su fecha de corte (${formatearFecha(estado.fecha_corte)}) hace de "hoy" para el modelo, aunque hoy sea ${estado.hoy ? formatearFecha(estado.hoy) : "otra fecha"}.`
                  : "Fecha de corte de los datos (el último día cargado), versión del modelo y origen de los datos"
              }
            >
              <Database size={14} aria-hidden />
              Datos al {formatearFecha(estado.fecha_corte)}
              {estado.version && <> · Modelo {estado.version}</>}
              {estado.datos_simulados && <> · Datos simulados</>}
            </p>
          )}

          <div className={styles.usuario}>
            <span className={styles.avatar} aria-hidden>
              {iniciales(usuario?.nombre_completo)}
            </span>
            <div className={styles.usuarioTexto}>
              <strong>{usuario?.nombre_completo}</strong>
              <span>{formatearRol(usuario?.rol)}</span>
            </div>
            <button type="button" className={styles.salir} onClick={logout}>
              <LogOut size={16} aria-hidden />
              Salir
            </button>
          </div>
        </header>

        <main className={styles.contenido}>
          <AvisoFecha estado={estado} />
          <Outlet />
        </main>
      </div>
    </div>
  );
}
