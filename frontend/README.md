# PredicTree · Frontend

Interfaz web de PredicTree (React + TypeScript + Vite).

| Comando          | Para qué                                                                 |
| ---------------- | ------------------------------------------------------------------------ |
| `npm install`    | Instala las dependencias (la primera vez o cuando cambie `package.json`) |
| `npm run dev`    | Inicia la interfaz en http://localhost:5173                              |
| `npm run build`  | Revisa los tipos de TypeScript y genera la versión final en `dist/`      |
| `npm run lint`   | Revisa errores comunes en el código                                      |
| `npm run format` | Ordena el formato del código con Prettier                                |

## Estructura de `src/`

| Carpeta       | Contenido                                                                |
| ------------- | ------------------------------------------------------------------------ |
| `pages/`      | Una pantalla por archivo (Dashboard, Carga de datos, Predicciones, etc.) |
| `layouts/`    | Estructura común: menú lateral y barra superior                          |
| `components/` | Piezas reutilizables (encabezados, tarjetas, tablas)                     |
| `auth/`       | Sesión del usuario: login, cierre de sesión y rutas protegidas           |
| `services/`   | Comunicación con la API (Axios)                                          |
| `config/`     | Configuración de la navegación del menú                                  |
| `types/`      | Tipos de TypeScript compartidos                                          |
| `styles/`     | Colores, tipografía y estilos globales (tomados del prototipo)           |
| `utils/`      | Funciones de ayuda (formato de textos, fechas, etc.)                     |
