"""Tarifa de referencia (editable por Revenue Management) y sugerencias de tarifa.

El sistema nunca cambia tarifas: solo calcula "tarifa sugerida = tarifa de referencia × (1 + ajuste)".
La tarifa de referencia puede ser:

* ``automatica``: el promedio de lo que ya está reservado para esa noche (o la tarifa de catálogo
  si todavía no hay reservas).
* ``manual``: las tarifas base que Revenue Management escribe por tipo de habitación, ponderadas por
  la mezcla de habitaciones reservadas esa noche.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.engine import Connection

MODOS = ("automatica", "manual")
CLAVE_MODO = "tarifa_referencia_modo"
PREFIJO = "tarifa_ref_"
TARIFA_MAXIMA = 20000.0


class TarifaInvalida(ValueError):
    pass


def tipos_habitacion(conexion) -> list[dict]:
    filas = conexion.execute(
        text(
            "SELECT codigo, nombre, cantidad, tarifa_base FROM tipo_habitacion ORDER BY tarifa_base"
        )
    ).all()
    return [
        {"codigo": f.codigo, "nombre": f.nombre, "cantidad": int(f.cantidad), "tarifa_base": float(f.tarifa_base)}
        for f in filas
    ]  # fmt: skip


def leer_referencia(conexion) -> tuple[str, dict[str, float]]:
    """(modo, tarifas por tipo). Si no hay configuración, el modo es automático."""
    params = {
        f.clave: f.valor
        for f in conexion.execute(
            text("SELECT clave, valor FROM parametro_sistema WHERE clave LIKE 'tarifa\\_ref%'")
        )
    }
    modo = params.get(CLAVE_MODO, "automatica")
    tarifas = {k[len(PREFIJO) :]: float(v) for k, v in params.items() if k.startswith(PREFIJO)}
    return (modo if modo in MODOS else "automatica"), tarifas


def guardar_referencia(conexion, modo: str, tarifas: dict[str, float]) -> None:
    """Valida y guarda la configuración. En modo manual hacen falta las tarifas de todos los tipos."""
    if modo not in MODOS:
        raise TarifaInvalida("El modo debe ser 'automatica' o 'manual'.")
    tipos = {t["codigo"]: t for t in tipos_habitacion(conexion)}
    desconocidos = set(tarifas) - set(tipos)
    if desconocidos:
        raise TarifaInvalida(f"Tipo de habitación desconocido: {', '.join(sorted(desconocidos))}.")
    if modo == "manual":
        faltan = [t["nombre"] for c, t in tipos.items() if c not in tarifas]
        if faltan:
            raise TarifaInvalida(f"Falta la tarifa de: {', '.join(faltan)}.")
    for codigo, valor in tarifas.items():
        if not (0 < valor <= TARIFA_MAXIMA):
            raise TarifaInvalida(
                f"La tarifa de {tipos[codigo]['nombre']} debe ser mayor que 0 y de hasta "
                f"S/ {TARIFA_MAXIMA:,.0f}.".replace(",", " ")
            )
    upsert = text(
        """
        INSERT INTO parametro_sistema (clave, valor, tipo_dato, descripcion, fecha_actualizacion)
        VALUES (:c, :v, :t, :d, now())
        ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor, fecha_actualizacion = now()
        """
    )
    conexion.execute(
        upsert,
        {
            "c": CLAVE_MODO, "v": modo, "t": "texto",
            "d": "Cómo se calcula la tarifa de referencia: automatica o manual (Revenue Management).",
        },
    )  # fmt: skip
    if modo == "manual":
        for codigo, valor in tarifas.items():
            conexion.execute(
                upsert,
                {
                    "c": PREFIJO + codigo, "v": f"{valor:.2f}", "t": "decimal",
                    "d": f"Tarifa de referencia por noche de {tipos[codigo]['nombre']} (PEN).",
                },
            )  # fmt: skip


def promedio_reservado(conexion, id_ejecucion: int | None = None) -> dict[str, float | None]:
    """Tarifa promedio por noche de las reservas vigentes, por tipo de habitación."""
    filas = conexion.execute(
        text(
            """
            SELECT tipo_habitacion, sum(num_habitaciones * tarifa_noche) / sum(num_habitaciones)
            FROM reserva WHERE estado_reserva = 'confirmada' GROUP BY 1
            """
        )
    ).all()
    return {f[0]: float(f[1]) for f in filas}


def _mezcla_por_noche(conexion, desde: date, hasta: date) -> dict[date, dict[str, float]]:
    """Habitaciones reservadas (confirmadas) por noche y tipo, entre ``desde`` y ``hasta``."""
    filas = conexion.execute(
        text(
            """
            SELECT d::date AS fecha, r.tipo_habitacion, sum(r.num_habitaciones) AS habs
            FROM reserva r
            CROSS JOIN LATERAL generate_series(
                greatest(r.fecha_llegada, :d), least(r.fecha_salida - 1, :h), interval '1 day') d
            WHERE r.estado_reserva = 'confirmada' AND r.fecha_salida > :d AND r.fecha_llegada <= :h
            GROUP BY 1, 2
            """
        ),
        {"d": desde, "h": hasta},
    ).all()
    mezcla: dict[date, dict[str, float]] = {}
    for f in filas:
        mezcla.setdefault(f.fecha, {})[f.tipo_habitacion] = float(f.habs)
    return mezcla


def recalcular_sugerencias(conexion: Connection, id_ejecucion: int) -> int:
    """Actualiza tarifa de referencia y tarifa sugerida de la ejecución. Devuelve cuántas filas."""
    modo, manual = leer_referencia(conexion)
    tipos = tipos_habitacion(conexion)
    catalogo = {t["codigo"]: t["tarifa_base"] for t in tipos}
    peso_catalogo = {t["codigo"]: t["cantidad"] for t in tipos}
    ref_tipo = manual if modo == "manual" else {}

    filas = conexion.execute(
        text(
            """
            SELECT s.id_sugerencia, s.ajuste_recomendado, o.fecha_analizada, o.tarifa_promedio
            FROM sugerencia_tarifa s
            JOIN riesgo_overbooking r USING (id_riesgo)
            JOIN ocupacion_esperada o USING (id_ocupacion)
            WHERE o.id_ejecucion = :e
            """
        ),
        {"e": id_ejecucion},
    ).all()
    if not filas:
        return 0
    fechas = [f.fecha_analizada for f in filas]
    mezcla = _mezcla_por_noche(conexion, min(fechas), max(fechas) + timedelta(days=1))
    total_catalogo = sum(peso_catalogo.values())
    tarifa_catalogo_prom = sum(catalogo[c] * peso_catalogo[c] for c in catalogo) / total_catalogo

    for f in filas:
        if modo == "manual":
            mix = mezcla.get(f.fecha_analizada) or peso_catalogo
            total = sum(mix.values())
            referencia = sum(ref_tipo[c] * h for c, h in mix.items() if c in ref_tipo) / total
        else:
            referencia = (
                float(f.tarifa_promedio) if f.tarifa_promedio is not None else tarifa_catalogo_prom
            )
        sugerida = referencia * (1 + float(f.ajuste_recomendado) / 100)
        conexion.execute(
            text(
                "UPDATE sugerencia_tarifa SET tarifa_referencia = :r, tarifa_sugerida = :s "
                "WHERE id_sugerencia = :i"
            ),
            {"r": round(referencia, 2), "s": round(sugerida, 2), "i": f.id_sugerencia},
        )
    return len(filas)
