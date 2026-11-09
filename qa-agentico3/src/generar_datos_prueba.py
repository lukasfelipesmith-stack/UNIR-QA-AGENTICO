"""
Genera el PAQUETE DE PRUEBA descargable desde la página (web/pruebas/).

Es independiente del experimento principal: usa otra semilla y otro periodo (marzo de 2026,
5 tiendas) y NO modifica datos/ ni resultados/, cuyos números están consignados en el TFM.

Archivos que produce:
  prueba_transacciones.csv     transacciones con 11 casos de error sembrados
  prueba_kpis.csv              KPIs mensuales publicados con 3 casos de error sembrados
  prueba_casos_esperados.csv   la "hoja de respuestas": qué errores hay, dónde y qué regla debe detectarlos
  LEEME_pruebas.txt            instrucciones
Uso:  python src/generar_datos_prueba.py
"""
import numpy as np
import pandas as pd

from generador_datos import RAIZ, generar_transacciones, calcular_kpis

SALIDA = RAIZ / "web" / "pruebas"
TIENDAS = ["T01", "T03", "T05", "T07", "T08"]


def _recalc(tx, i):
    u, p, d = tx.at[i, "unidades"], tx.at[i, "precio_lista"], tx.at[i, "descuento"]
    tx.at[i, "ingreso"] = round(u * p * (1 - d), 2)
    tx.at[i, "costo"] = u * tx.at[i, "costo_unitario"]
    tx.at[i, "margen"] = round(tx.at[i, "ingreso"] - tx.at[i, "costo"], 2)


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026)
    tx = generar_transacciones(inicio="2026-03-01", dias=31, semilla=2026)
    tx = tx[tx.tienda.isin(TIENDAS)].reset_index(drop=True)
    tx.insert(0, "id_transaccion", [f"TX{n:05d}" for n in range(1, len(tx) + 1)])
    casos = []

    def caso(tipo, ubic, desc, regla, archivo="prueba_transacciones.csv"):
        casos.append({"caso": f"C{len(casos)+1:02d}", "tipo": tipo, "archivo": archivo,
                      "ubicacion": ubic, "descripcion": desc, "regla_que_debe_detectarlo": regla})

    abiertas = tx.index[(tx.unidades > 0) & (tx.descuento > 0)]
    sel = rng.choice(abiertas, size=6, replace=False)
    for k, i in enumerate(sel[:3]):  # fórmula mal aplicada
        u, p, d = tx.at[i, "unidades"], tx.at[i, "precio_lista"], tx.at[i, "descuento"]
        tx.at[i, "ingreso"] = round(u * p * (1 - d) ** 2, 2) if k != 1 else round(u * p, 2)
        tx.at[i, "margen"] = round(tx.at[i, "ingreso"] - tx.at[i, "costo"], 2)
        caso("Cálculo", tx.at[i, "id_transaccion"], "descuento aplicado dos veces" if k != 1 else "descuento omitido", "R01 Fórmula del ingreso")
    i = sel[3]; tx.at[i, "unidades"] = -abs(int(tx.at[i, "unidades"])); _recalc(tx, i)
    caso("Datos", tx.at[i, "id_transaccion"], "unidades negativas", "R02 Valores inválidos")
    i = sel[4]; tx.at[i, "descuento"] = 1.5; _recalc(tx, i)
    caso("Datos", tx.at[i, "id_transaccion"], "descuento de 150 %", "R02 Valores inválidos")
    i = sel[5]; tx.at[i, "ingreso"] = np.nan
    caso("Datos", tx.at[i, "id_transaccion"], "ingreso vacío", "R02 Valores inválidos")

    domingos = tx.index[(tx.tamano == "pequena") & (tx.fecha_factura.dt.dayofweek == 6)]
    for i in rng.choice(domingos, size=2, replace=False):
        tx.at[i, "unidades"] = int(rng.integers(3, 8)); _recalc(tx, i)
        caso("Contextual", tx.at[i, "id_transaccion"], "venta en domingo en tienda pequeña (cerrada)", "R04 Tienda cerrada el domingo")

    normales = tx.index[(tx.unidades >= 4) & ~tx.index.isin(sel)]
    for i in rng.choice(normales, size=2, replace=False):
        tx.at[i, "unidades"] = int(tx.at[i, "unidades"] * 20); _recalc(tx, i)
        caso("Datos", tx.at[i, "id_transaccion"], "pico extremo de unidades (×20)", "Detección estadística")

    i = int(rng.choice(normales)); dup = tx.loc[[i]].copy()
    dup["id_transaccion"] = f"TX{len(tx)+1:05d}"
    tx = pd.concat([tx, dup], ignore_index=True)
    caso("Cálculo", f"{tx.at[i,'id_transaccion']} y {dup['id_transaccion'].iloc[0]}", "transacción duplicada", "R08 Duplicados")

    kp = calcular_kpis(tx.drop(columns="id_transaccion"))
    k = kp.set_index("tienda")
    bruto = (tx.unidades * tx.precio_lista).groupby(tx.tienda).sum()
    kp.loc[kp.tienda == "T03", "ingreso_total"] = round(float(bruto["T03"]), 2)
    caso("Semántica", "T03 | 2026-03", "ingreso mensual calculado antes del descuento", "R03 Ingreso mensual vs. recálculo", "prueba_kpis.csv")
    kp.loc[kp.tienda == "T07", "margen_pct"] = round(float(k.at["T07", "margen_total"] / k.at["T07", "costo_total"]), 4)
    caso("Semántica", "T07 | 2026-03", "margen dividido por el costo y no por el ingreso", "R05 Margen vs. recálculo", "prueba_kpis.csv")
    kp.loc[kp.tienda == "T05", "ingreso_total"] = round(float(k.at["T05", "ingreso_total"]) * 1.05, 2)
    caso("Cálculo", "T05 | 2026-03", "ingreso mensual inflado 5 % (doble conteo)", "R03 Ingreso mensual vs. recálculo", "prueba_kpis.csv")

    cols = ["id_transaccion", "fecha_pedido", "fecha_factura", "tienda", "tamano", "producto", "precio_lista",
            "unidades", "descuento", "ingreso", "costo_unitario", "costo", "margen"]
    tx[cols].to_csv(SALIDA / "prueba_transacciones.csv", index=False, date_format="%Y-%m-%d")
    kp[["tienda", "mes", "ingreso_total", "unidades_total", "costo_total", "margen_total", "margen_pct"]].to_csv(
        SALIDA / "prueba_kpis.csv", index=False)
    pd.DataFrame(casos).to_csv(SALIDA / "prueba_casos_esperados.csv", index=False)
    (SALIDA / "LEEME_pruebas.txt").write_text(
        "PAQUETE DE PRUEBA DEL REVISOR — Comercial Andina, marzo de 2026 (datos 100 % sintéticos)\n\n"
        f"prueba_transacciones.csv : {len(tx)} transacciones de 5 tiendas con 11 errores sembrados.\n"
        f"prueba_kpis.csv          : {len(kp)} KPIs mensuales publicados con 3 errores sembrados.\n"
        "prueba_casos_esperados.csv : la hoja de respuestas con los 14 casos y la regla que debe detectar cada uno.\n\n"
        "Cómo probar: en la página, sección 'Prueba el modelo', cargue los dos CSV (o use 'Usar datos de prueba')\n"
        "y compare las alertas con prueba_casos_esperados.csv. Puede editar los CSV para crear sus propios casos.\n"
        "Este paquete es independiente del experimento principal: sus resultados no cambian.\n", encoding="utf-8")
    print(f"Paquete de prueba en {SALIDA}: {len(tx)} transacciones, {len(kp)} KPIs, {len(casos)} casos")


if __name__ == "__main__":
    main()
