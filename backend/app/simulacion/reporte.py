"""Reporte de validación del realismo de los datos simulados.

Compara lo que generó el generador con las cifras que se pidieron (docs/supuestos_datos_simulados.md)
y verifica las reglas de coherencia. Se escribe en data/generados/reporte_validacion.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.simulacion.generador import (
    CANAL_OBJETIVO,
    POLITICA_OBJETIVO,
    PROCEDENCIA_OBJETIVO,
    SEGMENTO_OBJETIVO,
    ConfigGenerador,
)

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _tabla(columnas: list[str], filas: list[list[str]]) -> str:
    encabezado = "| " + " | ".join(columnas) + " |"
    separador = "|" + "|".join("---" for _ in columnas) + "|"
    cuerpo = ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas]
    return "\n".join([encabezado, separador, *cuerpo])


def _pct(valor: float, decimales: int = 1) -> str:
    return f"{valor * 100:.{decimales}f} %"


def verificar_coherencia(
    reservas: pd.DataFrame, cfg: ConfigGenerador, tipos: pd.DataFrame
) -> list[tuple[str, bool]]:
    """Reglas de coherencia del generador (docs, sección 6)."""
    corte = pd.Timestamp(cfg.fecha_corte)
    f_res = pd.to_datetime(reservas["fecha_reserva"])
    f_lle = pd.to_datetime(reservas["fecha_llegada"])
    f_sal = pd.to_datetime(reservas["fecha_salida"])
    f_can = pd.to_datetime(reservas["fecha_cancelacion"])
    estado = reservas["estado_reserva"]
    cancelada = estado == "cancelada"
    pasada = f_lle < corte
    capacidad = tipos.set_index("codigo")["capacidad_personas"]
    personas = reservas["adultos"] + reservas["ninos"]
    limite_personas = reservas["tipo_habitacion"].map(capacidad) * reservas["num_habitaciones"]
    codigos = reservas["codigo_reserva"]
    return [
        ("Reserva ≤ llegada < salida", bool(((f_res <= f_lle) & (f_lle < f_sal)).all())),
        ("Solo las canceladas tienen fecha de cancelación", bool((cancelada == f_can.notna()).all())),
        (
            "Cancelación entre la reserva y la llegada",
            bool(((f_can[cancelada] >= f_res[cancelada]) & (f_can[cancelada] <= f_lle[cancelada])).all()),
        ),
        ("Todas las reservas se hicieron antes del corte", bool((f_res < corte).all())),
        (
            "Llegadas antes del corte: estado final (completada, cancelada o no_show)",
            bool(estado[pasada].isin(["completada", "cancelada", "no_show"]).all()),
        ),
        (
            "Llegadas desde el corte: confirmada, o cancelada antes del corte",
            bool(
                estado[~pasada].isin(["confirmada", "cancelada"]).all()
                and (f_can[~pasada & cancelada] < corte).all()
            ),
        ),
        ("Adultos + niños ≤ capacidad de las habitaciones", bool((personas <= limite_personas).all())),
        ("Códigos únicos con formato DTL-AAAA-NNNNNN", bool(codigos.is_unique and codigos.str.match(r"^DTL-\d{4}-\d{6}$").all())),
        ("Tarifas positivas", bool((reservas["tarifa_noche"] > 0).all())),
    ]  # fmt: skip


def construir_reporte(
    reservas: pd.DataFrame,
    ocupacion: pd.DataFrame,
    info: dict,
    cfg: ConfigGenerador,
    tipos: pd.DataFrame,
) -> str:
    corte = pd.Timestamp(cfg.fecha_corte)
    capacidad = info["capacidad_total"]
    r = reservas.copy()
    r["f_res"] = pd.to_datetime(r["fecha_reserva"])
    r["f_lle"] = pd.to_datetime(r["fecha_llegada"])
    r["f_sal"] = pd.to_datetime(r["fecha_salida"])
    r["anticipacion"] = (r["f_lle"] - r["f_res"]).dt.days
    r["noches"] = (r["f_sal"] - r["f_lle"]).dt.days
    resueltas = r[r["f_lle"] < corte]
    futuras = r[r["f_lle"] >= corte]

    oc = ocupacion.copy()
    oc["f"] = pd.to_datetime(oc["fecha"])
    inicio_util = pd.Timestamp(cfg.fecha_inicio) + pd.Timedelta(days=cfg.dias_excluidos_inicio)
    hist = oc[(oc["f"] >= inicio_util) & (oc["f"] < corte)]

    out: list[str] = []
    out.append("# Reporte de validación de los datos simulados\n")
    out.append(
        f"Fecha de corte: **{cfg.fecha_corte:%d/%m/%Y}** · semilla: `{cfg.semilla}` · "
        f"capacidad: **{capacidad}** habitaciones.\n"
    )

    # ---- 1. Resumen -------------------------------------------------------------------------
    out.append("## 1. Resumen\n")
    por_estado = r["estado_reserva"].value_counts()
    filas = [[estado, f"{n:,}", _pct(n / len(r))] for estado, n in por_estado.items()]
    filas.append(["**Total**", f"**{len(r):,}**", "100 %"])
    out.append(_tabla(["Estado", "Reservas", "Porcentaje"], filas))
    out.append(
        f"\n- Llegadas del {r['f_lle'].min():%d/%m/%Y} al {r['f_lle'].max():%d/%m/%Y}; "
        f"hechas entre {r['f_res'].min():%d/%m/%Y} y {r['f_res'].max():%d/%m/%Y}."
        f"\n- Reservas rechazadas por falta de espacio (límite de sobreventa de "
        f"{info['limite_sobreventa']} habitaciones): **{info['reservas_denegadas']:,}**."
        f"\n- Calibración de la demanda: {info['iteraciones_calibracion']} ajustes "
        f"(escala final {info['escala_final']:.1f} reservas/día antes de temporada)."
    )

    # ---- 2. Ocupación -----------------------------------------------------------------------
    out.append("\n## 2. Ocupación real (noches antes del corte)\n")
    out.append(
        f"Se excluyen los primeros {cfg.dias_excluidos_inicio} días de enero 2024 porque la simulación "
        "arranca sin huéspedes que lleguen de diciembre.\n"
    )
    media = hist["ocupacion_pct"].mean()
    out.append(
        f"- Ocupación promedio: **{media:.1f} %** (objetivo {cfg.ocupacion_objetivo * 100:.0f} %)."
    )
    por_anio = hist.groupby(hist["f"].dt.year)["ocupacion_pct"].mean()
    out.append("- Por año: " + ", ".join(f"{a}: {v:.1f} %" for a, v in por_anio.items()) + ".")
    out.append(
        f"- Noches con ocupación ≥ 98 %: **{int((hist['ocupacion_pct'] >= 98).sum())}** de {len(hist)} "
        f"({_pct((hist['ocupacion_pct'] >= 98).mean())}). Ocupación mínima: {hist['ocupacion_pct'].min():.1f} %."
    )
    con_reub = hist[hist["reubicaciones"] > 0]
    out.append(
        f"- Noches con reubicaciones: **{len(con_reub)}** "
        f"({int(hist['reubicaciones'].sum())} huéspedes reubicados en total; "
        f"máximo en una noche: {int(hist['reubicaciones'].max())})."
    )
    mensual = hist.groupby([hist["f"].dt.year, hist["f"].dt.month])["ocupacion_pct"].agg(
        ["mean", "max"]
    )
    filas = [
        [f"{MESES[m - 1]} {a}", f"{fila['mean']:.1f} %", f"{fila['max']:.1f} %"]
        for (a, m), fila in mensual.iterrows()
    ]
    out.append("\n**Por mes**\n")
    out.append(_tabla(["Mes", "Promedio", "Máximo"], filas))
    semana = hist.groupby(hist["f"].dt.dayofweek)["ocupacion_pct"].mean()
    out.append("\n**Por día de la semana**\n")
    out.append(
        _tabla(["Día", "Ocupación promedio"], [[DIAS[d], f"{v:.1f} %"] for d, v in semana.items()])
    )
    top = hist.sort_values("ocupacion_pct", ascending=False).head(8)
    out.append("\n**Noches de mayor ocupación**\n")
    out.append(
        _tabla(
            ["Fecha", "Presentes", "Ocupación", "Reubicaciones"],
            [
                [f"{f:%d/%m/%Y}", int(p), f"{o:.1f} %", int(u)]
                for f, p, o, u in zip(top["f"], top["presentes"], top["ocupacion_pct"], top["reubicaciones"], strict=True)
            ],
        )
    )  # fmt: skip

    # ---- 3. Perfil de las reservas ---------------------------------------------------------
    out.append("\n## 3. Perfil de las reservas (todas) frente a lo esperado\n")

    def comparar(columna: str, objetivo: dict[str, float]) -> str:
        real = r[columna].value_counts(normalize=True)
        filas = [[k, _pct(v), _pct(real.get(k, 0.0))] for k, v in objetivo.items()]
        return _tabla([columna, "Esperado", "Generado"], filas)

    out.append(comparar("canal_reserva", CANAL_OBJETIVO) + "\n")
    out.append(comparar("segmento", SEGMENTO_OBJETIVO) + "\n")
    out.append(comparar("procedencia", PROCEDENCIA_OBJETIVO) + "\n")
    out.append(comparar("politica_tarifa", POLITICA_OBJETIVO) + "\n")
    out.append(
        f"- Noches por reserva: promedio **{r['noches'].mean():.2f}**, mediana **{r['noches'].median():.0f}** "
        "(esperado: mediana 2)."
        f"\n- Habitaciones por reserva: promedio **{r['num_habitaciones'].mean():.2f}**; "
        f"reservas de 5 o más habitaciones: {_pct((r['num_habitaciones'] >= 5).mean(), 2)}."
        f"\n- Huéspedes recurrentes: {_pct(r['huesped_recurrente'].mean())}."
    )
    ant = r.groupby("segmento")["anticipacion"].agg(["mean", "median", "max"])
    out.append("\n**Anticipación de la reserva (días)**\n")
    out.append(
        _tabla(
            ["Segmento", "Promedio", "Mediana", "Máximo"],
            [
                [s, f"{v['mean']:.1f}", f"{v['median']:.0f}", int(v["max"])]
                for s, v in ant.iterrows()
            ],
        )
    )

    # ---- 4. Cancelaciones y no-shows ------------------------------------------------------
    out.append("\n## 4. Cancelaciones y no-shows (llegadas antes del corte)\n")
    cancel = resueltas["estado_reserva"] == "cancelada"
    noshow = resueltas["estado_reserva"] == "no_show"
    out.append(
        f"- Cancelación total: **{_pct(cancel.mean())}** (esperado ≈ {_pct(cfg.cancelacion_objetivo, 0)})."
        f"\n- No-show total: **{_pct(noshow.mean(), 2)}** (esperado ≈ {_pct(cfg.noshow_objetivo, 0)}); "
        f"{int(noshow.sum()):,} casos."
    )
    filas = []
    for canal in CANAL_OBJETIVO:
        sub = resueltas[resueltas["canal_reserva"] == canal]
        flex = sub[sub["politica_tarifa"] == "flexible"]
        nr = sub[sub["politica_tarifa"] == "no_reembolsable"]
        filas.append(
            [
                canal,
                _pct((sub["estado_reserva"] == "cancelada").mean()),
                _pct((flex["estado_reserva"] == "cancelada").mean()),
                _pct((nr["estado_reserva"] == "cancelada").mean()),
                _pct((sub["estado_reserva"] == "no_show").mean(), 2),
            ]
        )
    out.append("\n**Por canal**\n")
    out.append(_tabla(["Canal", "Cancelación", "…flexible", "…no reembolsable", "No-show"], filas))

    resueltas = resueltas.assign(
        tramo=pd.cut(
            resueltas["anticipacion"],
            [-1, 7, 30, 90, 10_000],
            labels=["0-7 días", "8-30 días", "31-90 días", "más de 90 días"],
        )
    )
    por_tramo = resueltas.groupby("tramo", observed=True).apply(
        lambda g: pd.Series(
            {"n": len(g), "cancel": (g["estado_reserva"] == "cancelada").mean(), "noshow": (g["estado_reserva"] == "no_show").mean()}
        ),
        include_groups=False,
    )  # fmt: skip
    out.append(
        "\n**Por anticipación de la reserva** (así se ve la señal que el modelo debe aprender)\n"
    )
    out.append(
        _tabla(
            ["Anticipación", "Reservas", "Cancelación", "No-show"],
            [
                [t, f"{int(v['n']):,}", _pct(v["cancel"]), _pct(v["noshow"], 2)]
                for t, v in por_tramo.iterrows()
            ],
        )
    )
    filas = []
    for etiqueta, mascara in [
        ("Huésped recurrente", resueltas["huesped_recurrente"]),
        ("Huésped nuevo", ~resueltas["huesped_recurrente"]),
        ("Con cancelaciones previas", resueltas["cancelaciones_previas"] > 0),
        ("Extranjero", resueltas["procedencia"] == "extranjero"),
        ("Nacional", resueltas["procedencia"] == "nacional"),
    ]:
        sub = resueltas[mascara]
        filas.append(
            [etiqueta, f"{len(sub):,}", _pct((sub["estado_reserva"] == "cancelada").mean()), _pct((sub["estado_reserva"] == "no_show").mean(), 2)]
        )  # fmt: skip
    out.append("\n**Por perfil del huésped**\n")
    out.append(_tabla(["Perfil", "Reservas", "Cancelación", "No-show"], filas))

    # ---- 5. Tarifas ---------------------------------------------------------------------------
    out.append("\n## 5. Tarifas (soles por noche)\n")
    adr = r.groupby(r["f_lle"].dt.year)["tarifa_noche"].mean()
    out.append(
        "- Tarifa promedio por año de llegada: "
        + ", ".join(f"{a}: S/ {v:.0f}" for a, v in adr.items())
        + "."
    )
    por_tipo = r.groupby("tipo_habitacion")["tarifa_noche"].agg(["count", "mean", "min", "max"])
    out.append("\n")
    out.append(
        _tabla(
            ["Tipo", "Reservas", "Promedio", "Mínima", "Máxima"],
            [[t, f"{int(v['count']):,}", f"{v['mean']:.0f}", f"{v['min']:.0f}", f"{v['max']:.0f}"] for t, v in por_tipo.iterrows()],
        )
    )  # fmt: skip
    out.append(
        "\nReferencia pública: USD 92 a 150 por noche ≈ S/ 315 a 515 (la tarifa base de cada tipo cambia por temporada)."
    )

    # ---- 6. Reservas futuras ------------------------------------------------------------------
    out.append("\n## 6. Reservas futuras ya registradas (llegadas desde el corte)\n")
    fut_oc = oc[(oc["f"] >= corte)]
    out.append(
        f"- Reservas: **{len(futuras):,}** ({int((futuras['estado_reserva'] == 'confirmada').sum()):,} confirmadas, "
        f"{int((futuras['estado_reserva'] == 'cancelada').sum()):,} ya canceladas)."
    )
    filas = []
    for (a, m), g in fut_oc.groupby([fut_oc["f"].dt.year, fut_oc["f"].dt.month]):
        filas.append(
            [
                f"{MESES[m - 1]} {a}",
                f"{g['en_libros'].mean() / capacidad * 100:.1f} %",
                f"{g['en_libros'].max() / capacidad * 100:.1f} %",
            ]
        )
    out.append(
        "\n**Habitaciones en libros / capacidad (antes de cancelaciones y no-shows futuros)**\n"
    )
    out.append(_tabla(["Mes", "Promedio", "Máximo"], filas))
    out.append(
        "\nLas noches cercanas al corte tienen más reservas en libros que las lejanas: así se comporta un hotel real "
        "(la mayoría reserva con pocos días de anticipación)."
    )

    # ---- 7. Coherencia ----------------------------------------------------------------------
    out.append("\n## 7. Reglas de coherencia\n")
    verificaciones = verificar_coherencia(reservas, cfg, tipos)
    out.append(
        _tabla(
            ["Regla", "Resultado"],
            [[n, "✅ cumple" if ok else "❌ NO cumple"] for n, ok in verificaciones],
        )
    )
    out.append("")
    return "\n".join(out)


def resumen_corto(reservas: pd.DataFrame, ocupacion: pd.DataFrame, cfg: ConfigGenerador) -> str:
    """Resumen de unas líneas para mostrar en la consola."""
    corte = pd.Timestamp(cfg.fecha_corte)
    f_lle = pd.to_datetime(reservas["fecha_llegada"])
    resueltas = reservas[f_lle < corte]
    f = pd.to_datetime(ocupacion["fecha"])
    util = ocupacion[
        (f >= pd.Timestamp(cfg.fecha_inicio) + pd.Timedelta(days=cfg.dias_excluidos_inicio))
        & (f < corte)
    ]
    return (
        f"Reservas: {len(reservas):,} · ocupación media {util['ocupacion_pct'].mean():.1f} % · "
        f"cancelación {np.mean(resueltas['estado_reserva'] == 'cancelada') * 100:.1f} % · "
        f"no-show {np.mean(resueltas['estado_reserva'] == 'no_show') * 100:.2f} % · "
        f"noches con reubicaciones: {int((util['reubicaciones'] > 0).sum())}"
    )  # fmt: skip
