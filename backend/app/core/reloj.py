"""Fecha y hora de "hoy" según el hotel, sin depender de que el equipo tenga bien el reloj.

La predicción se calcula siempre con la *fecha de corte* de los datos (el último día cargado), así
que un reloj mal configurado no puede alterar los resultados del modelo. Este módulo solo sirve
para **avisar** cuando los datos no están al día o cuando la fecha del equipo parece incorrecta.

Orden de fuentes para saber "hoy":
1. La hora de internet (cabecera ``Date`` de sitios muy conocidos), pasada a la zona horaria del
   hotel (America/Lima). Se consulta con poca frecuencia y se guarda la diferencia con el reloj
   local.
2. Si no hay internet, el reloj del servidor, también pasado a la zona horaria del hotel.
"""

from __future__ import annotations

import time
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

SITIOS_HORA = (
    "https://www.google.com",
    "https://www.cloudflare.com",
    "https://www.microsoft.com",
)
SEGUNDOS_ESPERA = 2.0
VIGENCIA_OK = 30 * 60  # cuánto se reutiliza una consulta exitosa
VIGENCIA_FALLO = 5 * 60  # cuánto se espera antes de reintentar tras un fallo
# Si el reloj del equipo difiere de internet más que esto, se considera mal configurado.
DESVIO_TOLERADO = timedelta(minutes=10)

# (momento de la consulta con time.monotonic(), diferencia internet - equipo, o None si falló)
_cache: tuple[float, timedelta | None] | None = None


@dataclass(frozen=True)
class HoraHotel:
    ahora: datetime  # con zona horaria del hotel
    fuente: str  # "internet" o "equipo"
    reloj_equipo_correcto: bool | None  # None si no se pudo comparar con internet

    @property
    def hoy(self) -> date:
        return self.ahora.date()


def _consultar_internet() -> timedelta | None:
    """Diferencia (hora de internet − reloj del equipo), o None si no se pudo consultar."""
    for sitio in SITIOS_HORA:
        try:
            pedido = urllib.request.Request(sitio, method="HEAD")
            antes = datetime.now(UTC)
            with urllib.request.urlopen(pedido, timeout=SEGUNDOS_ESPERA) as r:  # noqa: S310
                cabecera = r.headers.get("Date")
            despues = datetime.now(UTC)
            if not cabecera:
                continue
            hora_servidor = parsedate_to_datetime(cabecera).astimezone(UTC)
            return hora_servidor - (antes + (despues - antes) / 2)
        except Exception:  # noqa: BLE001 - cualquier fallo de red significa "probar el siguiente"
            continue
    return None


def _diferencia_internet() -> timedelta | None:
    global _cache
    if not settings.verificar_hora_internet:
        return None
    ahora = time.monotonic()
    if _cache is not None:
        momento, diferencia = _cache
        vigencia = VIGENCIA_OK if diferencia is not None else VIGENCIA_FALLO
        if ahora - momento < vigencia:
            return diferencia
    diferencia = _consultar_internet()
    _cache = (ahora, diferencia)
    return diferencia


def hora_hotel() -> HoraHotel:
    """Hora actual en la zona horaria del hotel, corrigiendo el reloj si internet lo permite."""
    zona = ZoneInfo(settings.zona_horaria_hotel)
    local = datetime.now(UTC)
    diferencia = _diferencia_internet()
    if diferencia is None:
        return HoraHotel(local.astimezone(zona), "equipo", None)
    return HoraHotel(
        (local + diferencia).astimezone(zona), "internet", abs(diferencia) <= DESVIO_TOLERADO
    )


def reiniciar_cache() -> None:
    """Solo para pruebas."""
    global _cache
    _cache = None
