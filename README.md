# PredicTree

**Sistema de Predicción de Demanda y Riesgo de Overbooking mediante IA**
DoubleTree by Hilton Lima Miraflores · Área de Revenue Management

Proyecto académico del curso *Administración de Proyectos de Software* (UPN, 2026-2).
Trabaja únicamente con **datos simulados** generados por el equipo; no usa información real de huéspedes.

---

## Herramientas

| Componente | Tecnología |
|---|---|
| Interfaz web | React + TypeScript + Vite · React Router · Axios · Recharts · lucide-react |
| API (backend) | Python 3.13 + FastAPI + Uvicorn · Pydantic · SQLAlchemy |
| Base de datos | PostgreSQL (local) · pgAdmin 4 |
| Datos e IA | pandas · scikit-learn · SHAP · joblib |
| Reportes | openpyxl (Excel) · ReportLab (PDF) |
| Seguridad | JWT (PyJWT) · bcrypt |
| Calidad | pytest · Ruff · oxlint · Prettier |
| Equipo y diseño | Git + GitHub · Figma · VS Code |

## Estructura

```
predictree/
├── frontend/     Interfaz web (React + TypeScript)
├── backend/      API, reglas de negocio y modelo predictivo (FastAPI)
│   ├── app/
│   │   ├── api/        rutas (endpoints) y dependencias
│   │   ├── core/       configuración y seguridad
│   │   ├── db/         conexión a PostgreSQL
│   │   ├── models/     tablas (SQLAlchemy)
│   │   ├── schemas/    formatos de entrada y salida (Pydantic)
│   │   ├── services/   reglas de negocio: ocupación, riesgo, tarifas
│   │   └── ml/         modelo predictivo
│   ├── scripts/        tareas de consola (crear tablas, crear usuarios)
│   └── tests/          pruebas automáticas
├── database/     scripts SQL de la base de datos
├── data/         generador de datos simulados
├── notebooks/    análisis exploratorio y entrenamiento
├── models/       modelos entrenados (no se suben a GitHub)
└── docs/         documentación técnica
```

## Requisitos

- Python **3.13**
- Node.js **24 LTS** (o 20.19+ / 22.12+)
- PostgreSQL con pgAdmin 4
- Git

## Puesta en marcha (primera vez)

**1. Base de datos.** En pgAdmin ejecuta `database/00_crear_bd.sql` (una sentencia a la vez).

**2. Backend** (PowerShell, carpeta `backend`):

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env        # luego edita .env con tu contraseña y clave JWT
python -m scripts.init_db
python -m scripts.crear_usuario --usuario admin --nombre "Usuario demo"
python -m pytest
```

**3. Frontend** (otra ventana de PowerShell, carpeta `frontend`):

```powershell
npm install
Copy-Item .env.example .env
```

## Uso diario

| Qué | Dónde | Comando |
|---|---|---|
| Iniciar la API | `backend` (con `.venv` activado) | `uvicorn app.main:app --reload` |
| Iniciar la interfaz | `frontend` | `npm run dev` |
| Abrir la aplicación | navegador | http://localhost:5173 |
| Documentación de la API | navegador | http://127.0.0.1:8000/docs |
| Pruebas del backend | `backend` | `python -m pytest` |
| Revisar código Python | `backend` | `ruff check .` y `ruff format .` |
| Revisar código TypeScript | `frontend` | `npm run lint` y `npm run format` |

## Forma de trabajo del equipo

- `main` siempre debe funcionar. Cada tarea va en su propia rama: `git checkout -b feature/carga-datos`.
- Los cambios entran a `main` mediante **Pull Request** en GitHub, revisado por otro integrante.
- Antes de empezar a trabajar: `git checkout main` y `git pull`.
- Los archivos `.env` **nunca** se suben. Se comparten por mensaje privado; `.env.example` sirve de plantilla.
- Cambios en tablas: se editan los archivos de `database/` y se vuelve a ejecutar `python -m scripts.init_db`.

## Estado actual

- [x] Estructura del proyecto y herramientas configuradas
- [x] Login con usuario y contraseña (JWT) y rutas protegidas
- [x] Menú lateral y barra superior con el diseño del prototipo
- [ ] Script completo de las 12 tablas y vistas de reportes
- [ ] Generador de datos simulados
- [ ] Carga y validación de archivos
- [ ] Modelo predictivo de cancelación y no-show
- [ ] Ocupación esperada, riesgo, fechas críticas y sugerencias de tarifa
- [ ] Dashboard y reportes R-01 a R-04
