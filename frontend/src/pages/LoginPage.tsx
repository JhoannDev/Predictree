import { CircleAlert, Eye, EyeOff, LoaderCircle } from "lucide-react";
import { type FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import Logo from "../components/Logo";
import { mensajeDeError } from "../services/api";
import styles from "./LoginPage.module.css";

export default function LoginPage() {
  const { usuario, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const destino = (location.state as { desde?: string } | null)?.desde ?? "/dashboard";

  const [nombreUsuario, setNombreUsuario] = useState("");
  const [clave, setClave] = useState("");
  const [verClave, setVerClave] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (usuario) {
    return <Navigate to={destino} replace />;
  }

  async function handleSubmit(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await login(nombreUsuario.trim(), clave);
      navigate(destino, { replace: true });
    } catch (err) {
      setError(mensajeDeError(err, "No se pudo iniciar sesión."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className={styles.pantalla}>
      <div className={styles.tarjeta}>
        <section className={styles.formulario}>
          <Logo />
          <h1 className={styles.titulo}>Iniciar sesión</h1>
          <p className={styles.subtitulo}>Ingresa con las credenciales asignadas por el equipo.</p>

          <form onSubmit={handleSubmit} className={styles.campos} noValidate>
            <label className={styles.etiqueta}>
              Usuario
              <input
                className={styles.input}
                value={nombreUsuario}
                onChange={(e) => setNombreUsuario(e.target.value)}
                autoComplete="username"
                maxLength={30}
                required
                autoFocus
              />
            </label>

            <label className={styles.etiqueta}>
              Contraseña
              <span className={styles.claveContenedor}>
                <input
                  className={styles.input}
                  type={verClave ? "text" : "password"}
                  value={clave}
                  onChange={(e) => setClave(e.target.value)}
                  autoComplete="current-password"
                  maxLength={72}
                  required
                />
                <button
                  type="button"
                  className={styles.verClave}
                  onClick={() => setVerClave((valor) => !valor)}
                  aria-label={verClave ? "Ocultar contraseña" : "Mostrar contraseña"}
                >
                  {verClave ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </span>
            </label>

            {error && (
              <p className={styles.error} role="alert">
                <CircleAlert size={16} aria-hidden />
                {error}
              </p>
            )}

            <button
              type="submit"
              className={styles.boton}
              disabled={enviando || !nombreUsuario.trim() || !clave}
            >
              {enviando && <LoaderCircle size={18} className={styles.girando} aria-hidden />}
              {enviando ? "Ingresando…" : "Iniciar sesión"}
            </button>
          </form>
        </section>

        <aside className={styles.panel}>
          <p className={styles.panelEtiqueta}>Revenue Management</p>
          <h2 className={styles.lema}>
            Anticipa la ocupación.
            <br />
            Identifica el riesgo.
          </h2>
          <p className={styles.panelTexto}>
            Predicción de demanda y riesgo de overbooking mediante IA para el DoubleTree by Hilton
            Lima Miraflores.
          </p>
          <p className={styles.panelNota}>Proyecto académico · datos simulados</p>
        </aside>
      </div>
    </div>
  );
}
