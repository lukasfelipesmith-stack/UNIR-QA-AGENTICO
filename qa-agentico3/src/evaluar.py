"""
Paso 2 del experimento: ejecuta los 4 métodos de QA y los califica contra la verdad de referencia.

  (a) QA manual (simulado con supuestos explícitos)
  (b) Reglas genéricas (Pandera)
  (c) Machine learning (PyOD)
  (d) Framework agéntico (evaluador desde Gherkin + auditor del tablero + ML + alertas)

Uso:  python src/generar_escenario.py   y luego   python src/evaluar.py
"""
import json
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from generador_datos import RAIZ, cargar_contexto
from metodos_clasicos import reglas_genericas, ml_anomalias
from generar_pagina import main as generar_pagina
from framework_agentico import REGLAS_EVALUADOR, agente_evaluador, agente_auditor, generar_alertas

DATOS, RES = RAIZ / "datos", RAIZ / "resultados"
FAMILIAS = ["datos", "contextual", "calculo", "semantica", "visualizacion"]
METODOS = ["Manual (simulado)", "Reglas genéricas", "ML (PyOD)", "Framework agéntico"]

# Supuestos del QA manual (SIMULADO). Reemplazar con datos reales de Jira (Fase 1 de la metodología).
MANUAL = {
    "muestra_tx": 0.05, "seg_por_tx": 30, "min_por_kpi": 3, "min_por_total": 3, "min_por_celda_tablero": 1,
    "p_deteccion": {"A1": 0.90, "A2": 0.95, "A3": 0.40, "A4": 0.30, "A5": 0.25, "B1": 0.60,
                    "S1": 0.35, "S2": 0.40, "S3": 0.10, "S4": 0.30,
                    "V1": 0.50, "V2": 0.85, "V3": 0.70, "V4": 0.60},
}
# Supuestos de revisión humana en el framework (HITL): se reemplazan con resultados/decisiones_hitl.csv
HITL_MIN = {"crítica": 1.0, "media": 1.0, "alta": 5 / 60}


def cargar_datos():
    tx = pd.read_csv(DATOS / "transacciones.csv", index_col="fila", parse_dates=["fecha_pedido", "fecha_factura"])
    kpis = pd.read_csv(DATOS / "kpis.csv")
    totales = pd.read_csv(DATOS / "totales_compania.csv")
    tablero = json.loads((DATOS / "tablero.json").read_text(encoding="utf-8"))
    return tx, kpis, totales, tablero


def universo(tx, kpis, totales, tablero):
    u = {f"tx|{i}" for i in tx.index} | {f"kpi|{r.tienda}|{r.mes}" for r in kpis.itertuples()}
    u |= {f"total|{m}" for m in totales.mes}
    for m in tablero["meses"]:
        for v in m["visuales"]:
            u.add(f"tab|{m['mes_filtro']}|{v['id']}|TITULO")
            u |= {f"tab|{m['mes_filtro']}|{v['id']}|{c['tienda']}" for c in v["valores"]}
    return u


def metricas(pred, verdad, univ):
    pos = set(verdad["clave"])
    tp, fp, fn = len(pred & pos), len(pred - pos), len(pos - pred)
    p = tp / (tp + fp) if tp + fp else 0
    r = tp / (tp + fn) if tp + fn else 0
    out = {"TP": tp, "FP": fp, "FN": fn, "precision": round(p, 3), "recall": round(r, 3),
           "f1": round(2 * p * r / (p + r), 3) if p + r else 0}
    for f in FAMILIAS:
        claves = set(verdad.loc[verdad.familia == f, "clave"])
        out[f"recall_{f}"] = round(len(pred & claves) / len(claves), 3)
    return out


def manual_simulado(verdad, n_tx, n_kpi, n_tot, n_tab, n_sim=500, semilla=99):
    rng = np.random.default_rng(semilla)
    rec = {f: [] for f in FAMILIAS}
    tot = []
    for _ in range(n_sim):
        hall = np.zeros(len(verdad), bool)
        for k, a in enumerate(verdad.itertuples()):
            revisada = rng.random() < MANUAL["muestra_tx"] if a.clave.startswith("tx|") else True
            hall[k] = revisada and rng.random() < MANUAL["p_deteccion"][a.tipo]
        for f in FAMILIAS:
            rec[f].append(hall[(verdad.familia == f).values].mean())
        tot.append(hall.mean())
    horas = (n_tx * MANUAL["muestra_tx"] * MANUAL["seg_por_tx"] / 3600 + n_kpi * MANUAL["min_por_kpi"] / 60
             + n_tot * MANUAL["min_por_total"] / 60 + n_tab * MANUAL["min_por_celda_tablero"] / 60)
    out = {"TP": None, "FP": 0, "FN": None, "precision": 1.0, "recall": round(float(np.mean(tot)), 3)}
    out["f1"] = round(2 * out["recall"] / (1 + out["recall"]), 3)
    out.update({f"recall_{f}": round(float(np.mean(v)), 3) for f, v in rec.items()})
    return out, horas


def horas_revision(alertas_sev):
    return sum(HITL_MIN[s] for s in alertas_sev) / 60


def main():
    RES.mkdir(exist_ok=True)
    (RES / "reglas_generadas").mkdir(exist_ok=True)
    pipeline, estilo = cargar_contexto()
    catalogo = pipeline["fuentes"]["catalogo_tiendas"]
    tx, kpis, totales, tablero = cargar_datos()
    univ = universo(tx, kpis, totales, tablero)
    n_tab = sum(len(v["valores"]) for m in tablero["meses"] for v in m["visuales"])

    # (b) reglas genéricas
    t0 = time.perf_counter(); pred_b = reglas_genericas(tx, kpis, totales, tablero); t_b = time.perf_counter() - t0
    # (c) ML
    t0 = time.perf_counter(); ml = ml_anomalias(tx); pred_c = set(ml); t_c = time.perf_counter() - t0
    # (d) framework agéntico
    t0 = time.perf_counter()
    h_eval, pruebas = agente_evaluador(tx, kpis, totales, catalogo)
    h_aud = agente_auditor(tablero, kpis, totales, estilo)
    alertas = generar_alertas(h_eval, h_aud, ml)
    t_d = time.perf_counter() - t0
    pred_d = {a["clave"] for a in alertas}

    # ---- calificación (único punto donde se lee la verdad de referencia)
    verdad = pd.read_csv(DATOS / "anomalias_verdad.csv")
    m_a, horas_manual = manual_simulado(verdad, len(tx), len(kpis), len(totales), n_tab)
    res = {
        "Manual (simulado)": {**m_a, "horas_ciclo": round(horas_manual, 2)},
        "Reglas genéricas": {**metricas(pred_b, verdad, univ), "alertas": len(pred_b),
                             "horas_ciclo": round((t_b + 0) / 3600 + horas_revision(["alta"] * len(pred_b)), 2)},
        "ML (PyOD)": {**metricas(pred_c, verdad, univ), "alertas": len(pred_c),
                      "horas_ciclo": round(t_c / 3600 + horas_revision(["media"] * len(pred_c)), 2)},
        "Framework agéntico": {**metricas(pred_d, verdad, univ), "alertas": len(alertas),
                               "horas_ciclo": round(t_d / 3600 + horas_revision([a["severidad"] for a in alertas]), 2)},
    }
    tabla = pd.DataFrame(res).T[["precision", "recall", "f1"] + [f"recall_{f}" for f in FAMILIAS] + ["horas_ciclo"]]
    tabla.index.name = "metodo"
    tabla.to_csv(RES / "tabla_comparativa.csv")

    resumen = {
        "escenario": {"transacciones": len(tx), "celdas_kpi": len(kpis), "totales": len(totales),
                      "valores_tablero": n_tab, "anomalias": len(verdad),
                      "por_familia": verdad.familia.value_counts().to_dict()},
        "metodos": res,
        "pruebas_metamorficas_pipeline": pruebas,
        "segundos_ejecucion_framework": round(t_d, 2),
        "reduccion_tiempo_pct": round(100 * (1 - res["Framework agéntico"]["horas_ciclo"] / horas_manual), 1),
        "supuestos_manual": MANUAL, "supuestos_hitl_minutos": HITL_MIN,
    }
    (RES / "metricas.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (RES / "alertas.json").write_text(json.dumps(alertas, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    pd.DataFrame([{"regla": k, "feature": v[0], "escenario": v[1]} for k, v in REGLAS_EVALUADOR.items()]
                 + [{"regla": "T01", "feature": "05_tablero.feature", "escenario": "Los valores del tablero coinciden con los KPIs calculados"},
                    {"regla": "T02", "feature": "05_tablero.feature", "escenario": "Formato de moneda y porcentaje"},
                    {"regla": "T03", "feature": "05_tablero.feature", "escenario": "Títulos y periodo correctos"}]
                 ).to_csv(RES / "reglas_generadas" / "trazabilidad.csv", index=False)

    reporte_entrega(alertas, pruebas)
    graficos(tabla, horas_manual)
    print(tabla.to_string())
    generar_pagina()
    print(f"\nReducción del tiempo de ciclo: {resumen['reduccion_tiempo_pct']} % | alertas: {len(alertas)}")


def reporte_entrega(alertas, pruebas):
    df = pd.DataFrame(alertas)
    crit = df[df.severidad == "crítica"]
    lineas = ["# Reporte previo a la entrega — Comercial Andina", "",
              f"**Decisión sugerida: {'NO ENTREGAR' if len(crit) else 'ENTREGAR'}** "
              f"({len(crit)} alertas críticas pendientes de revisión humana).", "",
              "| Severidad | Alertas |", "| --- | --- |"]
    lineas += [f"| {s} | {n} |" for s, n in df.severidad.value_counts().items()]
    lineas += ["", "## Alertas críticas", ""]
    lineas += [f"- **{r.id}** ({r.regla}) {r.explicacion}" for r in crit.itertuples()]
    lineas += ["", "## Pruebas metamórficas del pipeline", ""]
    lineas += [f"- {p['regla']}: {p['resultado']}" for p in pruebas]
    (RES / "reporte_entrega.md").write_text("\n".join(lineas), encoding="utf-8")


def graficos(tabla, horas_manual):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    colores = ["#9AA5B1", "#E0A458", "#7A9E7E", "#2563EB"]
    nombres = {"datos": "Datos", "contextual": "Contextual", "calculo": "Cálculo",
               "semantica": "Semántica", "visualizacion": "Visualización"}
    x = np.arange(len(FAMILIAS)); w = 0.2
    fig, ax = plt.subplots(figsize=(10, 4.6))
    for k, met in enumerate(METODOS):
        ax.bar(x + (k - 1.5) * w, [tabla.loc[met, f"recall_{f}"] for f in FAMILIAS], w, label=met, color=colores[k])
    ax.set_xticks(x, [nombres[f] for f in FAMILIAS]); ax.set_ylim(0, 1.15)
    ax.set_ylabel("Recall (proporción de anomalías detectadas)")
    ax.set_title("Detección por familia de anomalía y método de QA")
    ax.legend(frameon=False, ncol=4, loc="upper center", fontsize=9)
    fig.tight_layout(); fig.savefig(RES / "fig1_recall_por_familia.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.2))
    met = ["precision", "recall", "f1"]; x = np.arange(len(met))
    for k, m in enumerate(METODOS):
        ax.bar(x + (k - 1.5) * w, [tabla.loc[m, c] for c in met], w, label=m, color=colores[k])
    ax.set_xticks(x, ["Precisión", "Recall", "F1"]); ax.set_ylim(0, 1.05)
    ax.set_title("Desempeño global por método")
    ax.legend(frameon=False, ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout(); fig.savefig(RES / "fig2_desempeno_global.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.2))
    vals = [horas_manual, tabla.loc["Framework agéntico", "horas_ciclo"]]
    ax.barh(["QA manual (simulado)", "Framework + revisión humana"], vals, color=[colores[0], colores[3]])
    for i, v in enumerate(vals):
        ax.text(v, i, f"  {v:.1f} h", va="center")
    ax.set_xlabel("Horas de QA por ciclo de entrega"); ax.set_xlim(0, max(vals) * 1.25)
    ax.set_title("Tiempo de ciclo de QA")
    fig.tight_layout(); fig.savefig(RES / "fig3_tiempo_ciclo.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    main()
