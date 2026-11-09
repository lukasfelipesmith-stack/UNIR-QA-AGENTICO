"""
Inyección programada y etiquetada de anomalías sintéticas (verdad de referencia).

Cada anomalía queda registrada en una lista con su clave de ubicación:
  tx|<fila>                      transacción
  kpi|<tienda>|<mes>             celda de KPI mensual
  total|<mes>                    total de la compañía
  tab|<mes>|<visual>|<tienda>    valor del tablero (tienda = TITULO para el título del visual)

Familias y tipos:
  datos          A1 pico extremo · A2 valor inválido
  contextual     A4 venta en día de cierre · A5 volumen anómalo para el tamaño de tienda
  calculo        A3 fórmula de ingreso mal aplicada · B1 doble conteo en el KPI mensual
  semantica      S1 ingreso antes del descuento · S2 margen sobre el costo ·
                 S3 mes agrupado por fecha_pedido · S4 total incluye tienda inactiva
  visualizacion  V1 valor del mes anterior · V2 formato de moneda incorrecto ·
                 V3 margen como proporción · V4 título equivocado
"""
import numpy as np
import pandas as pd

from generador_datos import calcular_kpis, calcular_totales, construir_tablero

FAMILIA = {
    "A1": "datos", "A2": "datos", "A4": "contextual", "A5": "contextual",
    "A3": "calculo", "B1": "calculo",
    "S1": "semantica", "S2": "semantica", "S3": "semantica", "S4": "semantica",
    "V1": "visualizacion", "V2": "visualizacion", "V3": "visualizacion", "V4": "visualizacion",
}
PLAN = {"A1": 60, "A2": 40, "A3": 60, "A4": 40, "A5": 40, "B1": 4,
        "S1": 4, "S2": 4, "S3": 4, "V1": 4, "V2": 4, "V3": 4, "V4": 3}


def _registrar(verdad, tipo, clave, detalle):
    verdad.append({"tipo": tipo, "familia": FAMILIA[tipo], "clave": clave, "detalle": detalle})


def _recalcular_fila(tx, i):
    u, p, d = tx.at[i, "unidades"], tx.at[i, "precio_lista"], tx.at[i, "descuento"]
    tx.at[i, "ingreso"] = round(u * p * (1 - d), 2)
    tx.at[i, "costo"] = u * tx.at[i, "costo_unitario"]
    tx.at[i, "margen"] = round(tx.at[i, "ingreso"] - tx.at[i, "costo"], 2)


def inyectar_transacciones(tx, verdad, semilla=7):
    rng = np.random.default_rng(semilla)
    tx = tx.copy()
    usadas = set()

    def elegir(n, mascara):
        cand = np.array([i for i in tx.index[mascara] if i not in usadas])
        sel = rng.choice(cand, size=n, replace=False)
        usadas.update(sel.tolist())
        return sel

    abierta = tx["unidades"] > 0
    pequena = tx["tamano"] == "pequena"
    domingo = tx["fecha_factura"].dt.dayofweek == 6

    for i in elegir(PLAN["A1"], abierta):
        tx.at[i, "unidades"] = int(tx.at[i, "unidades"] * rng.integers(10, 40)); _recalcular_fila(tx, i)
        _registrar(verdad, "A1", f"tx|{i}", "pico extremo de unidades")
    for k, i in enumerate(elegir(PLAN["A2"], abierta)):
        if k % 3 == 0:
            tx.at[i, "unidades"] = -abs(int(tx.at[i, "unidades"])); _recalcular_fila(tx, i); d = "unidades negativas"
        elif k % 3 == 1:
            tx.at[i, "descuento"] = float(rng.choice([1.5, 2.0, -0.2])); _recalcular_fila(tx, i); d = "descuento fuera de rango"
        else:
            tx.at[i, "ingreso"] = np.nan; d = "ingreso nulo"
        _registrar(verdad, "A2", f"tx|{i}", d)
    for k, i in enumerate(elegir(PLAN["A3"], abierta & (tx["descuento"] > 0))):
        u, p, d = tx.at[i, "unidades"], tx.at[i, "precio_lista"], tx.at[i, "descuento"]
        tx.at[i, "ingreso"] = round(u * p * (1 - d) ** 2, 2) if k % 2 == 0 else round(u * p, 2)
        tx.at[i, "margen"] = round(tx.at[i, "ingreso"] - tx.at[i, "costo"], 2)
        _registrar(verdad, "A3", f"tx|{i}", "descuento aplicado dos veces" if k % 2 == 0 else "descuento omitido")
    for i in elegir(PLAN["A4"], pequena & domingo):
        tx.at[i, "unidades"] = int(rng.integers(3, 8)); _recalcular_fila(tx, i)
        _registrar(verdad, "A4", f"tx|{i}", "venta registrada en domingo (tienda cerrada)")
    for i in elegir(PLAN["A5"], abierta & pequena):
        tx.at[i, "unidades"] = int(tx.at[i, "unidades"] * 5 + 6); _recalcular_fila(tx, i)
        _registrar(verdad, "A5", f"tx|{i}", "volumen de tienda grande en tienda pequeña")
    return tx


def inyectar_kpis(kpis, tx, verdad, semilla=11):
    """Errores en la capa de cálculo (B1) y errores semánticos (S1–S3)."""
    rng = np.random.default_rng(semilla)
    k = kpis.copy()
    n = PLAN["B1"] + PLAN["S1"] + PLAN["S2"] + PLAN["S3"]
    idx = list(rng.choice(k.index, size=n, replace=False))
    k_pedido = calcular_kpis(tx, columna_fecha="fecha_pedido").set_index(["tienda", "mes"])
    tx_mes = tx.assign(mes=tx["fecha_factura"].dt.to_period("M").astype(str),
                       bruto=tx["unidades"] * tx["precio_lista"])
    bruto = tx_mes.groupby(["tienda", "mes"])["bruto"].sum()

    for i in idx[:4]:
        k.at[i, "ingreso_total"] = round(k.at[i, "ingreso_total"] * rng.uniform(1.03, 1.08), 2)
        _registrar(verdad, "B1", f"kpi|{k.at[i,'tienda']}|{k.at[i,'mes']}", "filas duplicadas inflan el ingreso")
    for i in idx[4:8]:
        k.at[i, "ingreso_total"] = round(float(bruto.loc[(k.at[i, "tienda"], k.at[i, "mes"])]), 2)
        _registrar(verdad, "S1", f"kpi|{k.at[i,'tienda']}|{k.at[i,'mes']}", "ingreso calculado antes del descuento")
    for i in idx[8:12]:
        k.at[i, "margen_pct"] = round(k.at[i, "margen_total"] / k.at[i, "costo_total"], 4)
        _registrar(verdad, "S2", f"kpi|{k.at[i,'tienda']}|{k.at[i,'mes']}", "margen dividido por el costo")
    for i in idx[12:16]:
        k.at[i, "ingreso_total"] = round(float(k_pedido.loc[(k.at[i, "tienda"], k.at[i, "mes"]), "ingreso_total"]), 2)
        _registrar(verdad, "S3", f"kpi|{k.at[i,'tienda']}|{k.at[i,'mes']}", "mes agrupado por fecha_pedido")
    return k


def inyectar_totales(totales, kpis, verdad):
    """S4: el total de mayo y junio sigue sumando a T10 (cerrada) con su último valor."""
    t = totales.copy()
    ultimo_t10 = kpis[(kpis.tienda == "T10")].sort_values("mes")["ingreso_total"].iloc[-1]
    for mes in ["2026-05", "2026-06"]:
        t.loc[t.mes == mes, "ingreso_total"] += round(ultimo_t10, 2)
        _registrar(verdad, "S4", f"total|{mes}", "total incluye la tienda inactiva T10")
    return t


def inyectar_tablero(tablero, verdad, semilla=13):
    rng = np.random.default_rng(semilla)
    meses = tablero["meses"]
    usadas = set()

    def visual(m, vid):
        return next(v for v in meses[m]["visuales"] if v["id"] == vid)

    def elegir_celda(vid, desde_mes=0):
        while True:
            m = int(rng.integers(desde_mes, len(meses)))
            vals = visual(m, vid)["valores"]
            j = int(rng.integers(0, len(vals)))
            if (m, vid, j) not in usadas:
                usadas.add((m, vid, j))
                return m, vals[j]

    for _ in range(PLAN["V1"]):
        m, celda = elegir_celda("v_ingreso", desde_mes=1)
        previo = {c["tienda"]: c["valor"] for c in visual(m - 1, "v_ingreso")["valores"]}
        celda["valor"] = previo[celda["tienda"]]
        _registrar(verdad, "V1", f"tab|{meses[m]['mes_filtro']}|v_ingreso|{celda['tienda']}", "muestra el valor del mes anterior")
    for k in range(PLAN["V2"]):
        m, celda = elegir_celda("v_ingreso")
        num = int(celda["valor"].replace("$ ", "").replace(".", ""))
        celda["valor"] = f"USD {num/4000:,.0f}" if k % 2 == 0 else f"${num}"
        _registrar(verdad, "V2", f"tab|{meses[m]['mes_filtro']}|v_ingreso|{celda['tienda']}", "formato de moneda incorrecto")
    for _ in range(PLAN["V3"]):
        m, celda = elegir_celda("v_margen")
        pct = float(celda["valor"].replace(" %", "").replace(",", ".")) / 100
        celda["valor"] = f"{pct:.2f}".replace(".", ",")
        _registrar(verdad, "V3", f"tab|{meses[m]['mes_filtro']}|v_margen|{celda['tienda']}", "margen mostrado como proporción")
    titulos_falsos = ["Ventas brutas por tienda", "Margen bruto acumulado", "Ingreso total por región"]
    elegidos = rng.choice(len(meses) * 3, size=PLAN["V4"], replace=False)
    for k, e in enumerate(elegidos):
        m, vpos = divmod(int(e), 3)
        v = meses[m]["visuales"][vpos]
        v["titulo"] = titulos_falsos[k % len(titulos_falsos)]
        _registrar(verdad, "V4", f"tab|{meses[m]['mes_filtro']}|{v['id']}|TITULO", "título de visual equivocado")
    return tablero
