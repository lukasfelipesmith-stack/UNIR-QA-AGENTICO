"""
Líneas base clásicas (sin agentes):
  (b) Reglas genéricas de calidad de datos con Pandera: esquema, rangos y fórmula por fila.
      No conocen el negocio (no leen Gherkin ni pipeline.yaml).
  (c) Machine learning no supervisado con PyOD (Isolation Forest + Local Outlier Factor) sobre variables contextuales.
Ninguna lee datos/anomalias_verdad.csv.
"""
import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Check, Column
from pyod.models.lof import LOF
from pyod.models.iforest import IForest

TOL = 0.01

ESQUEMA_TX = pa.DataFrameSchema(
    {
        "unidades": Column(int, Check.ge(0)),
        "descuento": Column(float, Check.in_range(0, 1)),
        "ingreso": Column(float, Check.ge(0), nullable=False),
        "precio_lista": Column(int, Check.gt(0)),
    },
    checks=[Check(lambda d: (d["ingreso"] - d["unidades"] * d["precio_lista"] * (1 - d["descuento"])).abs() <= TOL,
                  name="columna_derivada_consistente", element_wise=False)],
)
ESQUEMA_KPI = pa.DataFrameSchema({
    "ingreso_total": Column(float, Check.gt(0), nullable=False),
    "margen_pct": Column(float, Check.in_range(-1, 1), nullable=False),
})


def _fallas(esquema, df):
    try:
        esquema.validate(df, lazy=True)
        return []
    except pa.errors.SchemaErrors as e:
        fc = e.failure_cases
        return sorted(set(fc.loc[fc["index"].notna(), "index"].astype(int)))


def reglas_genericas(tx, kpis, totales, tablero):
    claves = {f"tx|{i}" for i in _fallas(ESQUEMA_TX, tx)}
    claves |= {f"kpi|{kpis.at[i,'tienda']}|{kpis.at[i,'mes']}" for i in _fallas(ESQUEMA_KPI, kpis)}
    for m in tablero["meses"]:  # genérico: solo que no haya valores vacíos
        for v in m["visuales"]:
            for c in v["valores"]:
                if not str(c["valor"]).strip():
                    claves.add(f"tab|{m['mes_filtro']}|{v['id']}|{c['tienda']}")
    return claves


def _variables_contextuales(tx):
    d = tx.copy()
    d["dow"] = d["fecha_factura"].dt.dayofweek
    u = d["unidades"].clip(lower=0)
    g = d.assign(u=u).groupby(["tienda", "producto", "dow"])["u"]
    med = g.transform("median")
    mad = g.transform(lambda s: (s - s.median()).abs().median()) + 1
    return np.column_stack([
        (u - med) / mad,
        np.log1p(u) - np.log1p(med),
        np.log1p(u),
        (d["ingreso"].fillna(0) / u.replace(0, np.nan)).fillna(0) / d["precio_lista"],
    ])


def ml_anomalias(tx, contaminacion=0.015, semilla=0):
    """Devuelve claves marcadas y el puntaje de anomalía de cada una."""
    X = np.nan_to_num(_variables_contextuales(tx))
    # Estandarizar y romper empates: LOF falla con puntos idénticos (p. ej., días cerrados con 0 ventas)
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-9)
    X = X + np.random.default_rng(semilla).normal(0, 1e-3, X.shape)
    f = IForest(contamination=contaminacion, random_state=semilla, n_estimators=300).fit(X)
    e = LOF(contamination=contaminacion, n_neighbors=150).fit(X)
    puntaje = (pd.Series(f.decision_scores_).rank(pct=True) + pd.Series(e.decision_scores_).rank(pct=True)) / 2
    # Ensamble: se marca el porcentaje más atípico según el puntaje promedio de ambos modelos
    marca = (puntaje >= puntaje.quantile(1 - contaminacion)).values
    idx = tx.index[marca]
    return {f"tx|{i}": round(float(puntaje.iloc[k]), 3) for k, i in zip(np.where(marca)[0], idx)}
