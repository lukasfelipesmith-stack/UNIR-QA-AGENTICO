"""
Generador de datos sintéticos de Comercial Andina (empresa ficticia).

Simula la canalización analítica de un proyecto real en tres capas:
  capa 0: transacciones diarias (tienda x producto x día)
  capa 1: KPIs mensuales por tienda + total de la compañía (lo que calcula el ingeniero de datos)
  capa 2: tablero que ve el cliente (valores ya formateados, títulos, meses)
"""
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parent.parent
SEMILLA = 42

FACTOR_TAMANO = {"grande": 3.0, "mediana": 1.5, "pequena": 0.6}
PRODUCTOS = {  # producto: (precio lista COP, costo unitario COP, popularidad)
    "P01": (12000, 7000, 8), "P02": (25000, 15000, 5), "P03": (8000, 4500, 12),
    "P04": (45000, 30000, 2), "P05": (15000, 9000, 6), "P06": (32000, 20000, 3),
    "P07": (5000, 2500, 15), "P08": (60000, 42000, 1),
}
FACTOR_DIA = [0.9, 0.85, 0.9, 1.0, 1.2, 1.4, 0.7]  # lunes..domingo


def cargar_contexto():
    pipeline = yaml.safe_load((RAIZ / "contexto" / "pipeline.yaml").read_text(encoding="utf-8"))
    estilo = yaml.safe_load((RAIZ / "contexto" / "estilo_tablero.yaml").read_text(encoding="utf-8"))
    return pipeline, estilo


def tienda_activa(catalogo, tienda, mes):
    """True si la tienda está activa en algún día del mes (formato 'YYYY-MM')."""
    info = catalogo[tienda]
    inicio_mes = pd.Period(mes, "M").start_time
    hasta = info.get("activa_hasta")
    return hasta is None or pd.Timestamp(hasta) >= inicio_mes


def generar_transacciones(inicio="2026-01-01", dias=180, semilla=SEMILLA):
    pipeline, _ = cargar_contexto()
    catalogo = pipeline["fuentes"]["catalogo_tiendas"]
    rng = np.random.default_rng(semilla)
    filas = []
    for fecha in pd.date_range(inicio, periods=dias, freq="D"):
        dow = fecha.dayofweek
        estacional = 1 + 0.15 * np.sin(2 * np.pi * fecha.dayofyear / 365)
        for tienda, info in catalogo.items():
            hasta = info.get("activa_hasta")
            if hasta is not None and fecha > pd.Timestamp(hasta):
                continue  # tienda cerrada definitivamente (T10 desde mayo)
            tamano = info["tamano"]
            cerrada = tamano == "pequena" and dow == 6  # regla: pequeñas cierran domingo
            for prod, (precio, costo_u, pop) in PRODUCTOS.items():
                lam = pop * FACTOR_TAMANO[tamano] * FACTOR_DIA[dow] * estacional
                unidades = 0 if cerrada else int(rng.poisson(lam))
                descuento = float(rng.choice([0, 0, 0, 0.05, 0.10, 0.15]))
                ingreso = round(unidades * precio * (1 - descuento), 2)
                costo = unidades * costo_u
                filas.append({
                    "fecha_pedido": fecha - pd.Timedelta(days=int(rng.integers(0, 4))),
                    "fecha_factura": fecha,
                    "tienda": tienda, "tamano": tamano, "producto": prod,
                    "precio_lista": precio, "unidades": unidades, "descuento": descuento,
                    "ingreso": ingreso, "costo_unitario": costo_u, "costo": costo,
                    "margen": round(ingreso - costo, 2),
                })
    return pd.DataFrame(filas)


def calcular_kpis(tx: pd.DataFrame, columna_fecha="fecha_factura") -> pd.DataFrame:
    """KPIs mensuales por tienda (definición oficial de pipeline.yaml)."""
    df = tx.copy()
    df["mes"] = df[columna_fecha].dt.to_period("M").astype(str)
    k = df.groupby(["tienda", "mes"], as_index=False).agg(
        ingreso_total=("ingreso", "sum"), unidades_total=("unidades", "sum"),
        costo_total=("costo", "sum"), margen_total=("margen", "sum"))
    k["ingreso_total"] = k["ingreso_total"].round(2)
    k["margen_pct"] = (k["margen_total"] / k["ingreso_total"]).round(4)
    k["ticket_promedio"] = (k["ingreso_total"] / k["unidades_total"]).round(2)
    return k


def calcular_totales(kpis: pd.DataFrame, catalogo) -> pd.DataFrame:
    """Ingreso total de la compañía por mes: solo tiendas activas."""
    act = kpis[[tienda_activa(catalogo, t, m) for t, m in zip(kpis.tienda, kpis.mes)]]
    return act.groupby("mes", as_index=False).agg(ingreso_total=("ingreso_total", "sum")).round(2)


# ------------------------------------------------------------ formato del tablero
def fmt_cop(valor):
    """$ 1.234.567 (punto como separador de miles, sin decimales)."""
    return "$ " + f"{round(valor):,}".replace(",", ".")


def fmt_pct(proporcion):
    """0.2534 -> '25,3 %'"""
    return f"{proporcion * 100:.1f}".replace(".", ",") + " %"


def construir_tablero(kpis: pd.DataFrame, totales: pd.DataFrame, estilo) -> dict:
    titulos = {v["id"]: v["titulo_esperado"] for v in estilo["visuales"]}
    meses = []
    for mes in sorted(kpis["mes"].unique()):
        km = kpis[kpis.mes == mes].sort_values("tienda")
        total = totales.loc[totales.mes == mes, "ingreso_total"].iloc[0]
        meses.append({
            "mes_filtro": mes,
            "visuales": [
                {"id": "v_ingreso", "titulo": titulos["v_ingreso"], "mes_mostrado": mes,
                 "valores": [{"tienda": r.tienda, "valor": fmt_cop(round(r.ingreso_total, -3))} for r in km.itertuples()]},
                {"id": "v_margen", "titulo": titulos["v_margen"], "mes_mostrado": mes,
                 "valores": [{"tienda": r.tienda, "valor": fmt_pct(r.margen_pct)} for r in km.itertuples()]},
                {"id": "v_total", "titulo": titulos["v_total"], "mes_mostrado": mes,
                 "valores": [{"tienda": "TOTAL", "valor": fmt_cop(round(total, -3))}]},
            ],
        })
    return {"empresa": "Comercial Andina", "moneda": "COP", "meses": meses}
