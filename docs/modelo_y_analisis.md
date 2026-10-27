# Modelo de IA y análisis de PredicTree

Este documento explica **qué hace el modelo, cómo se entrena, cómo se mide y qué resultados da**.
Sirve de guía para la exposición. Los datos de reservas son **simulados** (ver
`supuestos_datos_simulados.md`), así que las cifras demuestran que el sistema funciona, no el
desempeño sobre datos reales del hotel.

## 1. Qué predice el sistema

1. **Por reserva:** la probabilidad de que se **presente**, **cancele** o sea **no-show**. Las tres
   suman 100 %. Cada predicción trae los **factores que la explican** (RF-13).
2. **Por noche (90 días):** la **ocupación esperada** en habitaciones y en % de la capacidad (240).
3. **Riesgo de overbooking** por noche: bajo (< 90 %), medio (90 % a < 98 %), alto (≥ 98 %).
4. **Fechas críticas** (riesgo alto) y una **sugerencia de tarifa** informativa por regla
   (alto +5 % a +8 %, medio 0 %, bajo −3 %). No se aplica ningún cambio automático.

## 2. Cómo aprende el modelo

* **Algoritmo:** `HistGradientBoostingClassifier` (scikit-learn), un solo modelo multiclase con tres
  clases: se presenta / cancela / no-show.
* **Variables** (20, solo las que se conocen al momento de predecir): canal, segmento, política de
  tarifa, tipo de habitación, procedencia, días hasta la llegada, días desde que reservó, noches,
  habitaciones, adultos, niños, tarifa frente a la tarifa base, huésped recurrente, cancelaciones
  previas, solicitudes especiales, día de la semana, mes, nivel de demanda del calendario, evento y
  feriado durante la estadía. **Nunca** se usa el estado final ni la fecha de cancelación (sería
  hacer trampa: es justo lo que se quiere predecir).
* **"Fotos" de cada reserva:** una reserva de hace 90 días que llega mañana ya "sobrevivió" casi todo
  el periodo en que se cancela; una que llega en 3 meses, no. Por eso se entrena con fotos de cada
  reserva al reservar y a 1, 3, 7, 14, 30 y 60 días antes de la llegada (solo si en ese día seguía
  vigente). Así las probabilidades son **condicionales** al momento en que se consultan.
* **División por tiempo (no al azar):** entrena con llegadas hasta feb 2026, valida (número de árboles
  y umbrales) con mar–abr 2026 y **evalúa con llegadas de may a oct 2026**, que el modelo no vio. El modelo final se reentrena con todo hasta abr 2026.

## 3. Ocupación esperada

Para cada noche:

```
ocupación esperada = habitaciones reservadas − cancelaciones estimadas − no-shows estimados + pickup
```

* Las cancelaciones y no-shows salen de sumar las probabilidades del modelo de cada reserva.
* El **pickup** son las reservas que **todavía no se hacen** (la gente reserva con pocos días de
  anticipación). Se estima con la historia: para cada distancia a la noche se ajusta
  `real ≈ a + b · reservas netas + c · patrón del día y del calendario`.
* **Desviación del Business Case, que hay que decir al exponer:** el Business Case describe la
  ocupación como reservadas − cancelaciones − no-shows. Sin el pickup esa cifra queda muy por debajo
  de la ocupación real (el error llega a 21 % a 7 días y 54 % a 30 días), así que se agregó.

## 4. Resultados (periodo de prueba may–oct 2026)

| Medida | Resultado | Meta | ¿Cumple? |
|---|---|---|---|
| Error de ocupación (MAPE), 7 / 14 / 30 / 60 / 90 días antes | 4,2 / 5,4 / 6,7 / 7,8 / 8,6 % | ≤ 15 % | Sí |
| F1 de cancelación | 0,31 (AUC 0,80) | ≥ 0,80 | No |
| F1 de no-show | 0,10 (AUC 0,64) | ≥ 0,75 | No |

Además, el **RNF-03** pide detectar al menos el 80 % de las noches de riesgo. En el periodo de prueba
hubo solo 9 noches con ocupación final ≥ 90 %: con aviso a 14 días y umbral de 90 % el modelo detecta
el 33 % (precisión 50 %); con una *alerta temprana* 5 puntos antes (85 %), el 56 %. **No se cumple** y se
muestra tal cual en la página *Modelo y métricas*.

Las cifras exactas se ven en la página *Modelo y métricas* (menú Sistema) y cambian ligeramente si
se vuelve a generar o reentrenar.

**Por qué el F1 queda bajo la meta, dicho con claridad:**

* Cancelar es poco frecuente (8 % de las reservas vigentes) y el no-show más aún (2 %). Con eventos
  tan raros, un F1 de 0,80 exigiría predecir casi perfectamente quién cancela, algo que ningún
  modelo logra con datos de reserva (el comportamiento real depende de factores que no se registran).
* Lo que sí se logra: probabilidades **bien calibradas** (si dice 20 %, cancela cerca del 20 %), un
  buen orden de riesgo (AUC 0,80 en cancelación) y un **error de ocupación** bajo, que es el objetivo
  real del negocio.
* **No se ajustó el generador de datos para forzar las metas.** Se probó qué pasaría con menos ruido
  y con efectos más fuertes: incluso sin ningún ruido el F1 de cancelación se queda cerca de 0,33. La
  conclusión es que la meta de F1 ≥ 0,80 no es alcanzable con este tipo de datos. Propuesta para el
  docente: mantener F1 y agregar AUC, calibración y MAPE de ocupación como indicadores principales.
* La referencia "solo calendario" (día de la semana + eventos, sin mirar reservas) tiene un error de
  9,3 %. El modelo la supera claramente a 7–30 días y solo un poco a 90 días: a mayor anticipación,
  más incertidumbre.

## 5. Explicación de cada predicción (RF-13)

Para cada reserva se calcula cuánto cambia la probabilidad de "no llegar" (cancelación + no-show) al
reemplazar cada dato por valores típicos de otras reservas (oclusión, una aproximación al método
SHAP). Se guardan los 4 factores más influyentes con su efecto en puntos porcentuales, en
`prediccion.factores_explicativos` (JSON).

## 6. Cómo ejecutarlo

Desde la carpeta `backend`, con el entorno virtual activado:

```powershell
python -m scripts.init_db            # aplica el esquema v4 (agrega pickup_estimado, sin borrar datos)
python -m scripts.entrenar_modelo    # entrena, evalúa y registra el modelo v1.0 (≈ 1 minuto)
python -m scripts.ejecutar_analisis  # predicciones, ocupación, riesgo, fechas críticas y tarifas
uvicorn app.main:app --reload        # API en http://127.0.0.1:8000
```

En otra terminal, carpeta `frontend`: `npm run dev` y abrir http://localhost:5173.

El modelo se guarda en `models/predictree_v1.0.joblib` (no se sube a GitHub); sus métricas quedan en
las tablas `version_modelo` y `evaluacion_modelo`.

## 7. Dónde está cada cosa

| Qué | Archivo |
|---|---|
| Variables y "fotos" | `backend/app/ml/features.py` |
| Entrenamiento y métricas | `backend/app/ml/modelo.py` |
| Ocupación esperada y pickup | `backend/app/ml/ocupacion.py` |
| Explicación de predicciones | `backend/app/ml/explicacion.py` |
| Análisis completo (guarda en la base) | `backend/app/services/analisis.py` |
| Consultas compartidas (noches, banda de error) | `backend/app/services/consultas.py` |
| Tarifa de referencia y sugerencias | `backend/app/services/tarifas.py` |
| Endpoints | `routes/analisis.py` (`/api/dashboard`, `/api/predicciones`, `/api/modelo`, `/api/analisis/ejecutar`), `routes/consultas.py` (`/api/estado`, `/api/ocupacion`, `/api/riesgo`, `/api/noches/{fecha}`), `routes/tarifas.py` (`/api/tarifas`, `/api/tarifas/referencia`) |
| Pantallas | `frontend/src/pages/`: `DashboardPage`, `PrediccionesPage`, `OcupacionPage`, `RiesgoPage`, `FechasCriticasPage`, `TarifasPage`, `ModeloPage` |

## 8. Banda de error y tarifa de referencia

* **Margen de error de cada noche:** se toma el MAPE medido por horizonte (7, 14, 30, 60 y 90 días),
  se interpola según los días que faltan y se muestra como una franja alrededor de la ocupación
  esperada. Así se ve que las fechas lejanas son más inciertas.
* **Tarifa de referencia editable:** `parametro_sistema` guarda `tarifa_referencia_modo`
  (`automatica` o `manual`) y `tarifa_ref_<tipo>`. En modo manual, Revenue Management escribe la tarifa
  base de cada tipo de habitación y la referencia de cada noche es el promedio ponderado por la mezcla
  de habitaciones reservadas esa noche. En modo automático es el promedio de lo ya reservado. La
  tarifa sugerida = referencia × (1 + ajuste de la regla). Nunca se cambia una tarifa real.
