"""
(d) Framework de QA con IA agéntica — prototipo inicial (v1).

Capa 1  Contexto: contexto/criterios/*.feature, pipeline.yaml, estilo_tablero.yaml
Capa 2  Núcleo:
   - Agente evaluador de reglas: cada escenario Gherkin -> una regla ejecutable (REGLAS_EVALUADOR).
     En v1 las reglas fueron generadas por un LLM (Claude) a partir de los .feature, en modo asistido,
     y revisadas por el investigador. La v2 automatiza este paso con Claude Agent SDK + gx-mcp-server.
   - Agente auditor del tablero: valores, formatos, títulos y periodo (05_tablero.feature).
   - Detector estadístico: PyOD (metodos_clasicos.ml_anomalias).
Capa 3  Gobernanza: alertas con severidad y explicación de negocio -> revisión humana (revision_humana.py).
Ningún módulo lee datos/anomalias_verdad.csv.
"""
import re

import numpy as np
import pandas as pd

from generador_datos import calcular_kpis, tienda_activa
from metodos_clasicos import ml_anomalias

TOL = 0.01


def _clave_kpi(r):
    return f"kpi|{r.tienda}|{r.mes}"


# ------------------------------------------------------------------ AGENTE EVALUADOR
# Trazabilidad: id de regla -> archivo .feature y escenario de origen.
REGLAS_EVALUADOR = {
    "R01": ("01_ingreso_neto.feature", "Ingreso de cada transacción descuenta el descuento"),
    "R02": ("01_ingreso_neto.feature", "Ingreso de cada transacción descuenta el descuento (nunca negativo ni nulo)"),
    "R03": ("01_ingreso_neto.feature", "Ingreso neto mensual por tienda usa la fecha de factura"),
    "R04": ("01_ingreso_neto.feature", "Las tiendas pequeñas no venden los domingos"),
    "R05": ("02_margen.feature", "Margen calculado sobre el ingreso"),
    "R06": ("02_margen.feature", "Margen dentro de rango razonable"),
    "R07": ("03_total_compania.feature", "Solo se suman tiendas activas"),
    "R08": ("03_total_compania.feature", "No hay duplicados en la agregación"),
    "R09": ("04_consistencia_metamorfica.feature", "La suma de las partes es igual al total"),
    "R10": ("04_consistencia_metamorfica.feature", "Reordenar los datos no cambia los KPIs"),
    "R11": ("04_consistencia_metamorfica.feature", "Duplicar precios duplica el ingreso pero no las unidades"),
}


def agente_evaluador(tx, kpis, totales, catalogo):
    """Ejecuta las reglas generadas desde el Gherkin. Devuelve hallazgos y pruebas del pipeline."""
    h = []

    def add(regla, clave, observado, esperado, detalle):
        h.append({"regla": regla, "clave": clave, "observado": observado, "esperado": esperado, "detalle": detalle})

    esperado_ing = tx["unidades"] * tx["precio_lista"] * (1 - tx["descuento"])
    for i in tx.index[(tx["ingreso"] - esperado_ing).abs() > TOL]:
        add("R01", f"tx|{i}", tx.at[i, "ingreso"], round(esperado_ing[i], 2), "ingreso no corresponde a unidades × precio × (1 − descuento)")
    malos = tx["ingreso"].isna() | (tx["ingreso"] < 0) | (tx["unidades"] < 0) | ~tx["descuento"].between(0, 0.5)
    for i in tx.index[malos]:
        add("R02", f"tx|{i}", tx.at[i, "ingreso"], "≥ 0 y no nulo", "valor inválido (negativo, nulo o descuento fuera de 0–0,5)")
    cerrado = (tx["tamano"] == "pequena") & (tx["fecha_factura"].dt.dayofweek == 6) & (tx["unidades"] != 0)
    for i in tx.index[cerrado]:
        add("R04", f"tx|{i}", int(tx.at[i, "unidades"]), 0, "venta en domingo en tienda pequeña (cerrada)")
    dup = tx.duplicated(["fecha_factura", "tienda", "producto"], keep=False)
    for i in tx.index[dup]:
        add("R08", f"tx|{i}", "duplicado", "único", "combinación fecha_factura + tienda + producto repetida")

    rec = calcular_kpis(tx).set_index(["tienda", "mes"])  # recálculo por la definición oficial
    for r in kpis.itertuples():
        e = rec.loc[(r.tienda, r.mes)]
        if abs(r.ingreso_total - e.ingreso_total) > 1:
            add("R03", _clave_kpi(r), r.ingreso_total, round(e.ingreso_total, 2), "ingreso mensual no coincide con la suma por fecha_factura")
        if abs(r.margen_pct - e.margen_pct) > 0.0005:
            add("R05", _clave_kpi(r), r.margen_pct, e.margen_pct, "margen % no corresponde a (ingreso − costo) / ingreso")
        if not 0 <= r.margen_pct <= 0.6:
            add("R06", _clave_kpi(r), r.margen_pct, "0–0,6", "margen fuera de rango razonable")

    for t in totales.itertuples():
        mes_k = kpis[kpis.mes == t.mes]
        act = np.array([tienda_activa(catalogo, x, t.mes) for x in mes_k.tienda])
        suma_activas = mes_k.loc[act, "ingreso_total"].sum()
        inactivas = sorted(mes_k.loc[~act, "tienda"])
        if inactivas or abs(t.ingreso_total - suma_activas) > 1:
            add("R07", f"total|{t.mes}", t.ingreso_total, round(suma_activas, 2),
                "el total no corresponde solo a las tiendas activas del catálogo" + (f" (aparecen {inactivas})" if inactivas else ""))
        if abs(t.ingreso_total - mes_k["ingreso_total"].sum()) > 1:
            add("R09", f"total|{t.mes}", t.ingreso_total, round(mes_k["ingreso_total"].sum(), 2), "la suma de las tiendas no es igual al total publicado")

    # Pruebas metamórficas sobre el código del pipeline (no sobre los datos)
    base = calcular_kpis(tx).sort_values(["tienda", "mes"]).reset_index(drop=True)
    barajado = calcular_kpis(tx.sample(frac=1, random_state=1)).sort_values(["tienda", "mes"]).reset_index(drop=True)
    doble = calcular_kpis(tx.assign(precio_lista=tx.precio_lista * 2,
                                    ingreso=tx.ingreso * 2)).sort_values(["tienda", "mes"]).reset_index(drop=True)
    pruebas = [
        {"regla": "R10", "resultado": "superada" if np.allclose(base.ingreso_total, barajado.ingreso_total) else "fallida"},
        {"regla": "R11", "resultado": "superada" if (np.allclose(doble.ingreso_total, base.ingreso_total * 2)
                                                    and (doble.unidades_total == base.unidades_total).all()) else "fallida"},
    ]
    return h, pruebas


# ------------------------------------------------------------------ AGENTE AUDITOR
RE_COP = re.compile(r"^\$ \d{1,3}(\.\d{3})*$")
RE_PCT = re.compile(r"^\d{1,3},\d %$")


def agente_auditor(tablero, kpis, totales, estilo):
    h = []
    titulos = {v["id"]: v["titulo_esperado"] for v in estilo["visuales"]}
    kp = kpis.set_index(["tienda", "mes"])
    tot = totales.set_index("mes")["ingreso_total"]

    def add(regla, clave, observado, esperado, detalle):
        h.append({"regla": regla, "clave": clave, "observado": observado, "esperado": esperado, "detalle": detalle})

    for m in tablero["meses"]:
        mes = m["mes_filtro"]
        for v in m["visuales"]:
            if v["titulo"] != titulos[v["id"]]:
                add("T03", f"tab|{mes}|{v['id']}|TITULO", v["titulo"], titulos[v["id"]], "título del visual distinto al definido")
            if v.get("mes_mostrado") != mes:
                add("T03", f"tab|{mes}|{v['id']}|TITULO", v.get("mes_mostrado"), mes, "el mes mostrado no coincide con el filtro")
            for c in v["valores"]:
                clave = f"tab|{mes}|{v['id']}|{c['tienda']}"
                val = c["valor"]
                if v["id"] in ("v_ingreso", "v_total"):
                    if not RE_COP.match(val):
                        add("T02", clave, val, "$ 1.234.567", "formato de moneda COP incorrecto"); continue
                    num = int(val[2:].replace(".", ""))
                    ref = kp.loc[(c["tienda"], mes), "ingreso_total"] if v["id"] == "v_ingreso" else tot[mes]
                    if abs(num - ref) > 500:
                        add("T01", clave, val, f"≈ {round(ref, -3):,.0f}".replace(",", "."), "valor del tablero distinto al KPI calculado")
                else:
                    if not RE_PCT.match(val):
                        add("T02", clave, val, "25,3 %", "formato de porcentaje incorrecto"); continue
                    pct = float(val.replace(" %", "").replace(",", "."))
                    ref = kp.loc[(c["tienda"], mes), "margen_pct"] * 100
                    if abs(pct - ref) > 0.051:
                        add("T01", clave, val, f"{ref:.1f} %", "margen del tablero distinto al KPI")
    return h


# ------------------------------------------------------------------ CAPA 3: ALERTAS
SEVERIDAD = {"R03": "crítica", "R05": "crítica", "R07": "crítica", "R09": "crítica",
             "T01": "crítica", "T02": "alta", "T03": "alta",
             "R01": "alta", "R02": "alta", "R04": "alta", "R06": "alta", "R08": "alta", "ML": "media"}


def explicar(a):
    """Explicación en lenguaje de negocio (plantilla; en v2 la redacta el LLM en lote)."""
    partes = a["clave"].split("|")
    if partes[0] == "tx":
        donde = "una transacción del detalle de ventas"
    elif partes[0] == "kpi":
        donde = f"el KPI de la tienda {partes[1]} en {partes[2]}"
    elif partes[0] == "total":
        donde = f"el ingreso total de la compañía de {partes[1]}"
    else:
        donde = f"el tablero ({partes[2]}, {partes[3]}) de {partes[1]}"
    return f"Se encontró un problema en {donde}: {a['detalle']}. Valor observado: {_fmt(a['observado'])}; esperado: {_fmt(a['esperado'])}."


def _fmt(v):
    if isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v):
        if abs(v) >= 1000:
            return "$ " + f"{round(v):,}".replace(",", ".")
        if abs(v) < 1 and v != 0:
            return f"{v*100:.1f}".replace(".", ",") + " %"
    return str(v)


def generar_alertas(hall_eval, hall_aud, ml):
    alertas = {}
    for a in hall_eval + hall_aud:
        prev = alertas.get(a["clave"])
        if prev is None or ["media", "alta", "crítica"].index(SEVERIDAD[a["regla"]]) > ["media", "alta", "crítica"].index(prev["severidad"]):
            alertas[a["clave"]] = {**a, "severidad": SEVERIDAD[a["regla"]]}
    for clave, p in ml.items():
        if clave not in alertas:
            alertas[clave] = {"regla": "ML", "clave": clave, "observado": f"puntaje {p}", "esperado": "comportamiento habitual",
                              "detalle": "patrón inusual frente al histórico de la tienda, producto y día", "severidad": "media"}
    out = []
    for n, a in enumerate(alertas.values(), 1):
        archivo, esc = REGLAS_EVALUADOR.get(a["regla"], ("05_tablero.feature" if a["regla"].startswith("T") else "—", "—"))
        out.append({"id": f"AL-{n:04d}", "severidad": a["severidad"], "regla": a["regla"], "criterio_origen": f"{archivo} · {esc}",
                    "clave": a["clave"], "observado": str(a["observado"]), "esperado": str(a["esperado"]),
                    "explicacion": explicar(a), "requiere_revision_humana": a["severidad"] in ("crítica", "media")})
    return out
