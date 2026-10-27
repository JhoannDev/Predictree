# Supuestos de los datos simulados — PredicTree

PredicTree no tiene acceso a datos reales del DoubleTree by Hilton Lima Miraflores. Por eso el equipo
genera **datos propios simulados**, con reglas definidas a partir de **fuentes públicas** de hotelería y
turismo. Este documento es la especificación del generador y la justificación ante el docente.

> **Importante:** el modelo aprende los patrones con que se generaron los datos. Sus métricas muestran
> que el sistema funciona de punta a punta, no el desempeño frente a un hotel real.

Cada valor indica su origen: **[Fuente]** = dato público; **[Supuesto]** = decisión del equipo basada en
esas fuentes.

---

## 1. Periodo y volumen

| Concepto | Valor |
|---|---|
| Fecha de corte ("hoy" de la simulación) | **31/10/2026** (parámetro `fecha_corte`) |
| Historia de reservas | Llegadas del **01/01/2024 al 30/10/2026** (~34 meses) |
| Reservas futuras | Llegadas del **31/10/2026 al 28/01/2027** (horizonte de 90 días) |
| Volumen | **≈ 72 000 reservas** en total (≈ 24 000 por año; el valor exacto sale del generador) |

**Por qué al menos 2 años:** el modelo debe ver cada temporada (fin de año, Fiestas Patrias, verano)
**dos veces o más**: una para aprender el patrón y otra para comprobar que lo predice bien. Con un solo
año, la evaluación tendría que hacerse sobre temporadas que el modelo nunca vio. Con ~34 meses se puede:

| Uso | Periodo |
|---|---|
| Entrenamiento | 01/2024 – 04/2026 (incluye 2 fines de año y 2 Fiestas Patrias) |
| Prueba del modelo (F1) | 05/2026 – 10/2026 (incluye Fiestas Patrias 2026 y una serie de conciertos masivos en octubre) |
| Prueba de ocupación (MAPE) | Últimos 90 días antes del corte: ocupación esperada vs. real |

**Cálculo del volumen [Supuesto]:** 240 habitaciones × 68 % de ocupación ≈ 163 habitaciones ocupadas
por noche. Con estancias de ~2.6 noches y ~1.14 habitaciones por reserva → ≈ 55 llegadas efectivas por
día. Sumando cancelaciones (~14 %) y no-shows (~2 %) → ≈ 66 reservas por día ≈ 24 000 al año
(≈ 72 000 en todo el periodo).

---

## 2. El hotel

| Concepto | Valor | Origen |
|---|---|---|
| Capacidad | **240 habitaciones** | [Supuesto] Decisión del equipo; listados públicos indican ~241 |
| Moneda | **Soles (PEN)** | [Supuesto] Decisión del equipo |
| Tipo de cambio de referencia | S/ 3.43 por USD (octubre 2026) | [Fuente] SUNAT, vía Cámara de Comercio de Lima |

**Inventario por tipo de habitación** (tabla `tipo_habitacion`):

| Tipo | Cantidad | Tarifa base (S/) | Origen |
|---|---|---|---|
| Estándar King | 150 | 390 | [Supuesto] reparto del equipo |
| Estándar Doble | 70 | 420 | [Supuesto] reparto del equipo |
| Junior Suite | 16 | 650 | [Fuente] el hotel ofrece junior suites con acceso al Executive Lounge |
| Suite | 4 | 1 150 | [Fuente] el hotel describe cuatro suites senior |

**Tarifas [Fuente + Supuesto]:** las tarifas publicadas del hotel rondan **USD 92 a 150 por noche**
(≈ S/ 315 a 515). Sobre la tarifa base se aplican [Supuesto]:

- Temporada y fechas especiales: tarifa × `factor_demanda` (tabla `fecha_especial`).
- Fines de semana: −8 % (menor demanda corporativa).
- Tarifa no reembolsable: −10 % frente a la flexible (práctica común para asegurar la venta).
- Variación aleatoria de ±5 %.

---

## 3. Demanda y estacionalidad

| Concepto | Valor | Origen |
|---|---|---|
| Ocupación promedio anual | **≈ 68 %** | [Fuente] hoteles de Lima reportan más de 60 %; cadenas nacionales proyectan más de 73 % |
| Picos por eventos | **92 % a 100 %** | [Fuente] Lima llegó a 92-95 % en un fin de semana con una final deportiva internacional (2025) |
| Julio y agosto | Demanda alta (factor 1.10) | [Fuente] MINCETUR: ~308 mil llegadas en julio y ~303 mil en agosto 2024, sobre el promedio de ~271 mil al mes |
| Enero y febrero | Demanda baja corporativa (factor 0.92) | [Fuente + Supuesto] el primer trimestre 2024 promedió ~256 mil llegadas al mes; vacaciones de verano reducen viajes de negocio |
| Lunes a jueves | Más negocios | [Supuesto] hotel urbano en Miraflores |
| Viernes a domingo | Más ocio | [Supuesto] |

**Fechas especiales (tabla `fecha_especial`, 2024-2027):**

- **16 feriados nacionales por año** vigentes desde 2024 [Fuente: El Peruano, Caretas]. Semana Santa se
  calcula cada año (2024: 28-29 mar; 2025: 17-18 abr; 2026: 2-3 abr; 2027: 25-26 mar).
- **Temporadas:** alta de julio-agosto, fin de año (20 dic - 3 ene) y baja corporativa (enero-febrero).
- **Eventos (5, con nombres genéricos):** el sistema no depende de ningún artista ni evento concreto, sino
  de la **categoría** del evento (`concierto_masivo`, `evento_deportivo`, `cumbre_internacional`,
  `congreso_feria`). Los eventos no son recurrentes (`recurrente = FALSE`); los feriados y temporadas sí.

  | Evento | Categoría | Fechas | `factor_demanda` |
  |---|---|---|---|
  | Cumbre internacional de líderes | `cumbre_internacional` | 10-16/11/2024 | 1.40 |
  | Final deportiva internacional | `evento_deportivo` | 28-30/11/2025 | 1.35 |
  | Concierto masivo internacional | `concierto_masivo` | 20/05/2026 | 1.10 |
  | Serie de conciertos masivos | `concierto_masivo` | 07-10/10/2026 | 1.30 |
  | Congreso internacional de negocios | `congreso_feria` | 17-19/11/2026 | 1.25 |

  Las fechas de los cuatro primeros están **inspiradas en eventos reales de Lima** [Fuente + Supuesto]. El
  último es **inventado** [Supuesto] y cae dentro del horizonte de predicción, para que la demostración
  muestre cómo el sistema anticipa un evento futuro.
- `factor_demanda` es un **[Supuesto]** del efecto en la demanda del hotel (por ejemplo, Semana Santa
  0.90 porque muchos limeños salen de la ciudad; una cumbre internacional 1.40).

---

## 4. Perfil de las reservas

| Variable | Distribución | Origen |
|---|---|---|
| Canal | OTA 40 %, web Hilton 25 %, corporativo 20 %, agencia 10 %, teléfono 5 % | [Supuesto] según D-EDGE: las OTA dominan la venta digital y la web propia es el segundo canal |
| Segmento | Ocio 45 %, negocios 35 %, grupo 10 %, evento 10 % | [Fuente + Supuesto] 16-17 % de turistas extranjeros viene por negocios (PROMPERÚ) y prefiere hoteles de 4-5 estrellas en Lima; en un hotel corporativo de Miraflores la proporción es mayor |
| Procedencia | Extranjero 70 %, nacional 30 % | [Fuente + Supuesto] Lima recibe al 79 % de los turistas extranjeros (PROMPERÚ 2025) |
| Noches | Mediana 2, promedio ~2.6 (1 a 10) | [Fuente + Supuesto] en Lima la permanencia mediana es 3 noches y el promedio 5 (PROMPERÚ 2024); en un mismo hotel la estancia es más corta |
| Anticipación | Negocios: 0-21 días; ocio/OTA: 0-120 días (promedio ~30); grupos y eventos: 30-180 días | [Supuesto] |
| Política de tarifa | Flexible 75 %, no reembolsable 25 % | [Supuesto] D-EDGE recomienda más tarifas no reembolsables para reducir cancelaciones |
| Habitaciones por reserva | 1 en la mayoría (promedio ~1.14); bloques de grupos y eventos de 5 a 30 | [Supuesto] |

---

## 5. Comportamiento: cancelaciones y no-shows

**Tasas base por canal, con tarifa flexible** [Fuente + Supuesto]:

| Canal | Cancelación | No-show |
|---|---|---|
| OTA | 26 % | 3.0 % |
| Agencia de viajes | 15 % | 2.5 % |
| Corporativo | 12 % | 1.5 % |
| Teléfono | 10 % | 1.5 % |
| Web Hilton (directo) | 9 % | 1.0 % |

- **Fuentes:** D-EDGE reporta que Booking.com cancela cerca de 1 de cada 4 reservas, casi el triple que
  la venta directa, con una cancelación general de 13-14 % en Asia-Pacífico (2024-2025). El no-show
  promedio de la industria es de 1 a 2 % de las reservas (guía de Visa para hoteles), más alto en
  intermediarios como las OTA (Chalupa et al., 2025).
- **Tarifa no reembolsable:** cancelación de ~3 %, porque el huésped pierde el pago.
- **Anticipación:** a más días entre la reserva y la llegada, más probabilidad de cancelar. [Supuesto]
- **Huésped recurrente:** menos cancelación y no-show. [Supuesto]
- **Cancelaciones previas:** más probabilidad de volver a cancelar. [Supuesto]

**Resultado esperado del conjunto [Supuesto]:** cancelación total ≈ 14 % y no-show ≈ 2 %, coherente con
las fuentes. El no-show es un caso poco frecuente: es normal que su F1 sea más difícil de alcanzar que el
de cancelación.

---

## 6. Reglas de coherencia del generador

1. **Estados según la fecha de corte:**
   - Llegada **antes** del 31/10/2026 → `completada`, `cancelada` o `no_show` (resultado conocido).
   - Llegada **desde** el 31/10/2026 → `confirmada`, o `cancelada` si la cancelación ocurrió antes del corte.
2. **Fechas:** reserva ≤ llegada < salida; si es cancelada, reserva ≤ fecha de cancelación ≤ llegada.
3. **Capacidad:** el hotel acepta reservas por encima de las 240 habitaciones (hasta 264 en libros, un 10 % más: sobreventa), porque espera
   cancelaciones y no-shows: ese es el riesgo que PredicTree estima. Casi siempre la sobreventa se
   compensa con cancelaciones y no-shows, pero en pocas noches de alta demanda se presentan más huéspedes
   que habitaciones: ese exceso se registra como `reubicaciones_reales` y la `ocupacion_real` nunca
   supera las 240.
4. **Huéspedes:** adultos + niños ≤ capacidad del tipo de habitación.
5. **Códigos:** `DTL-AAAA-NNNNNN` (por ejemplo `DTL-2025-004213`). Sin datos personales.
6. **Reproducible:** semilla aleatoria fija, así todo el equipo obtiene exactamente los mismos datos.

---

## 7. Realismo del generador y métricas del modelo

**Realismo.** Los datos son inventados, pero se diseñan para comportarse como los de un hotel real
[Supuesto, decisión del equipo]:

- **Crecimiento** de la demanda de ~6 % anual [Supuesto], coherente con la recuperación del turismo
  receptivo en Perú (en 2024 todavía no alcanzaba los niveles prepandemia).
- **Variación aleatoria** diaria: no se generan curvas perfectas.
- **Sobreventa controlada** en noches de alta demanda, con **reubicaciones** cuando se presentan más
  huéspedes que habitaciones (regla 3 de la sección 6). El Business Case busca reducir las reubicaciones
  en 15 %, por eso se registran en `ocupacion_esperada.reubicaciones_reales`.
- **Historia sin errores.** La validación de datos se muestra con un archivo aparte de demostración
  ("reservas nuevas de noviembre") que lleva ~2 % de errores a propósito.
- **Reporte de validación** después de generar: ocupación por mes, cancelación por canal, no-show y tarifa
  promedio frente a las cifras públicas de la sección 4 y 5.

**Métricas.** Se prioriza el realismo y no se ajustan los datos para forzar una métrica:

- El **no-show es un evento raro** (~2 %), por lo que su F1 por reserva es más difícil de alcanzar que el
  de cancelación. El generador incluirá factores que influyen de verdad en el no-show (canal, política de
  tarifa, anticipación, huésped recurrente, cancelaciones previas), para que el modelo tenga patrones
  reales que aprender. Cargar más filas no ayuda: la dificultad es la poca señal, no la falta de datos.
- Lo que PredicTree necesita para decidir es la **ocupación esperada por noche**, que usa los no-shows
  como cantidades esperadas agregadas; su exactitud se mide con el **MAPE de ocupación (meta ≤ 15 %)**.
- Se reportará el F1 obtenido junto con precision y recall, tal como salga. Si el F1 de no-show queda por
  debajo de la meta de 0.75, se explica con esta sección y se gestiona como control de cambios.

---

## 8. Cómo se generan y dónde quedan

El generador está en `backend/app/simulacion/` y se ejecuta con `python -m scripts.generar_datos`
(desde la carpeta `backend`). Lee el calendario, los tipos de habitación y los parámetros de la base de
datos, y escribe en `data/generados/` (no se sube a GitHub):

| Archivo | Contenido |
|---|---|
| `reservas_historial.csv` | Todas las reservas simuladas (historia y reservas futuras ya registradas) |
| `ocupacion_real_por_noche.csv` | Habitaciones en libros, huéspedes presentes, ocupación % y reubicaciones por noche |
| `reporte_validacion.md` | Comparación de lo generado con las cifras de este documento y reglas de coherencia |

Después carga las reservas en la tabla `reserva` con un `lote_carga` de `origen_datos = 'generador'`.
Con la misma semilla siempre salen exactamente los mismos datos.

---

## 9. Fuentes consultadas

- Feriados 2026: Caretas — https://caretas.pe/nacional/feriados-2026-los-16-dias-de-descanso-oficial-en-el-peru/
- Feriados 2024 (16 desde 2024): El Peruano — https://elperuano.pe/noticia/231090-feriados-2024-en-peru-conoce-aqui-el-calendario-de-dias-festivos-para-este-ano
- Ocupación en Lima y efecto de una cumbre internacional: Gestión — https://gestion.pe/economia/empresas/miraflores-contara-con-700-nuevas-habitaciones-hoteleras-en-2025-quienes-estan-detras-noticia/
- Ocupación de hoteles 2025: Forbes Perú — https://forbes.pe/negocios/2025-09-08/como-avanza-el-turismo-internacional-en-peru-esto-responden-hoteleros-y-aerolineas
- Ocupación de Lima en un fin de semana con final deportiva internacional (2025): Gestión — https://gestion.pe/economia/empresas/costa-del-sol-pone-a-revision-fecha-para-reinicio-de-obras-de-segundo-hotel-en-jorge-chavez-noticia/
- Cancelaciones por canal (D-EDGE, Asia-Pacífico 2025): TravelMole — https://travelmole.com/news/d-edge-booking-hotels-asia
- Cancelaciones en Europa (D-EDGE): Hospitality Technology — https://hospitalitytech.com/global-cancellation-rate-hotel-reservations-reaches-40-average
- No-show promedio de la industria (guía Visa): https://www.belizebank.com/wp-content/uploads/2019/03/Prevent-and-Handle-No-Shows-A-guide-for-Hotel-Owners-and-Managers.pdf
- Cancelaciones y no-shows por canal: Chalupa et al. (2025) — https://doi.org/10.20867/thm.32.3.1
- Permanencia en Lima: PROMPERÚ, Perfil del Turista Extranjero 2024 — https://www.promperu.gob.pe/turismoin/archivos/cifraspdf/pte%2024%20-%20visita%20lima.pdf
- Motivo de viaje y destinos (2025): Gestión — https://gestion.pe/peru/promperu-cuanto-gastan-los-turistas-extranjeros-que-visitan-el-peru-y-cuanto-se-quedan-noticia/
- Llegadas de julio 2024: Andina — https://andina.pe/agencia/noticia-turismo-receptivo-crecio-41-el-peru-primeros-siete-meses-2024-997663.aspx
- Llegadas del primer trimestre 2024: Caretas — https://caretas.pe/nacional/mincetur-durante-el-primer-trimestre-del-2024-al-peru-llegaron-mas-de-700-mil-turistas-internacionales
- Llegadas de agosto 2024: COMEXPERÚ — https://www.comexperu.org.pe/upload/articles/reportes/boletin-turismo-038.pdf
- Total de llegadas 2024: El Tiempo — https://eltiempo.pe/economia/el-turismo-extranjero-en-peru-crecio-un-29-en-2024-pero-aun-no-recupera-niveles-prepandemia/
- Tarifas de DoubleTree en Lima: Skyscanner — https://espanol.skyscanner.com/hoteles/peru/lima-hoteles/ci-27544067/doubletree/b-90718360
- Tipos de habitación del hotel: Pleasant Holidays — https://www.pleasantholidays.com/South-America-Hotels-El-Pardo-Doubletree-By-Hilton-Hotel
- Suites del hotel: Airshop — https://www.airshop.gr/en/hotel/Peru/-El-Pardo-Doubletree-By-Hilton/44643
- Tipo de cambio (19/10/2026): Cámara de Comercio de Lima — https://lacamara.pe/?p=102254
- Agenda de conciertos masivos 2026 en Lima: Perú21 — https://peru21.pe/espectaculos/conciertos-2026-en-peru-guia-completa-de-fechas-artistas-y-escenarios/
