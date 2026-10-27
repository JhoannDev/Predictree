import { useCallback, useEffect, useState } from "react";
import { mensajeDeError } from "../services/api";

interface Estado<T> {
  datos: T | null;
  cargando: boolean;
  error: string | null;
}

/** Carga datos de la API al abrir la pantalla (y cada vez que cambian las dependencias). */
export function useCarga<T>(cargar: () => Promise<T>, dependencias: unknown[] = []) {
  const [estado, setEstado] = useState<Estado<T>>({ datos: null, cargando: true, error: null });
  const [intento, setIntento] = useState(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const cargarMemo = useCallback(cargar, dependencias);

  useEffect(() => {
    let vigente = true;
    setEstado((e) => ({ ...e, cargando: true, error: null }));
    cargarMemo()
      .then((datos) => vigente && setEstado({ datos, cargando: false, error: null }))
      .catch(
        (e) => vigente && setEstado({ datos: null, cargando: false, error: mensajeDeError(e) }),
      );
    return () => {
      vigente = false;
    };
  }, [cargarMemo, intento]);

  return { ...estado, recargar: () => setIntento((n) => n + 1) };
}
