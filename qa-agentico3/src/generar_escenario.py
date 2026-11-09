"""
Paso 1 del experimento: crea el escenario de prueba de Comercial Andina.

Salidas en datos/:
  transacciones.csv, kpis.csv, totales_compania.csv, tablero.json  -> lo que recibe el QA (con errores escondidos)
  anomalias_verdad.csv                                              -> lista secreta, SOLO para calificar
"""
import json

import pandas as pd

from generador_datos import (RAIZ, cargar_contexto, generar_transacciones, calcular_kpis,
                             calcular_totales, construir_tablero)
from inyector_anomalias import inyectar_transacciones, inyectar_kpis, inyectar_totales, inyectar_tablero

DATOS = RAIZ / "datos"


def main():
    DATOS.mkdir(exist_ok=True)
    pipeline, estilo = cargar_contexto()
    catalogo = pipeline["fuentes"]["catalogo_tiendas"]
    verdad = []

    tx = inyectar_transacciones(generar_transacciones(), verdad)
    kpis = inyectar_kpis(calcular_kpis(tx), tx, verdad)
    totales = inyectar_totales(calcular_totales(kpis, catalogo), kpis, verdad)
    tablero = inyectar_tablero(construir_tablero(kpis, totales, estilo), verdad)

    tx.to_csv(DATOS / "transacciones.csv", index_label="fila", date_format="%Y-%m-%d")
    kpis.to_csv(DATOS / "kpis.csv", index=False)
    totales.to_csv(DATOS / "totales_compania.csv", index=False)
    (DATOS / "tablero.json").write_text(json.dumps(tablero, ensure_ascii=False, indent=1), encoding="utf-8")
    pd.DataFrame(verdad).to_csv(DATOS / "anomalias_verdad.csv", index=False)

    v = pd.DataFrame(verdad)
    print(f"Transacciones: {len(tx):,} | celdas KPI: {len(kpis)} | anomalías inyectadas: {len(v)}")
    print(v.groupby(["familia", "tipo"]).size().to_string())


if __name__ == "__main__":
    main()
