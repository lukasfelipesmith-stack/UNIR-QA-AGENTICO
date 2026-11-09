"""
Genera web/index.html: página interactiva de resultados del prototipo (para Vercel).
Lee resultados/, contexto/ y datos/ y los incrusta en una sola página (sin servidor).

Uso:  python src/generar_pagina.py   (evaluar.py la llama al final)
Para mostrar el botón del repositorio, escribe su dirección en REPO_URL.
"""
import base64
import csv
import json
import shutil
from collections import Counter

import yaml

from generador_datos import RAIZ

REPO_URL = ""  # p. ej. "https://github.com/TU-USUARIO/qa-agentico"
RES, WEB, CTX = RAIZ / "resultados", RAIZ / "web", RAIZ / "contexto"


def recolectar_datos():
    metricas = json.loads((RES / "metricas.json").read_text(encoding="utf-8"))
    alertas = json.loads((RES / "alertas.json").read_text(encoding="utf-8"))
    with open(RES / "reglas_generadas" / "trazabilidad.csv", encoding="utf-8") as f:
        traza = list(csv.DictReader(f))
    features = [{"archivo": p.name, "texto": p.read_text(encoding="utf-8")}
                for p in sorted((CTX / "criterios").glob("*.feature"))]
    jira = yaml.safe_load((CTX / "linea_base_jira.yaml").read_text(encoding="utf-8"))
    with open(RAIZ / "datos" / "anomalias_verdad.csv", encoding="utf-8") as f:
        verdad = list(csv.DictReader(f))
    tipos = Counter((v["familia"], v["tipo"], v["detalle"].split(" (")[0]) for v in verdad)
    familias = {}
    for (fam, tipo, det), n in tipos.items():
        familias.setdefault(fam, {}).setdefault(tipo, {"n": 0, "ej": det})["n"] += n
    pr = WEB / "pruebas"
    pruebas = None
    if (pr / "prueba_transacciones.csv").exists():
        with open(pr / "prueba_casos_esperados.csv", encoding="utf-8") as f:
            casos = list(csv.DictReader(f))
        pruebas = {"tx": (pr / "prueba_transacciones.csv").read_text(encoding="utf-8"),
                   "kpis": (pr / "prueba_kpis.csv").read_text(encoding="utf-8"), "casos": casos}
    return {"m": metricas, "alertas": alertas, "traza": traza, "features": features,
            "jira": jira, "familias": familias, "repo": REPO_URL, "pruebas": pruebas}


def archivos_incrustados():
    """Todo lo descargable va dentro de la página: funciona aunque solo se suba index.html."""
    a = {}
    for carpeta in ("pruebas", "descargas"):
        for f in sorted((WEB / carpeta).iterdir()):
            if f.suffix == ".png":
                a[f.name] = {"tipo": "image/png", "b64": base64.b64encode(f.read_bytes()).decode()}
            else:
                tipo = {".csv": "text/csv", ".md": "text/markdown", ".txt": "text/plain"}.get(f.suffix, "text/plain")
                a[f.name] = {"tipo": tipo, "texto": f.read_text(encoding="utf-8-sig")}
    return a


def preparar_descargas():
    """Copia a web/descargas/ los resultados del experimento en formatos fáciles de abrir (no modifica resultados/)."""
    d = WEB / "descargas"
    d.mkdir(parents=True, exist_ok=True)
    alertas = json.loads((RES / "alertas.json").read_text(encoding="utf-8"))
    with open(d / "alertas_experimento.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["id", "severidad", "regla", "criterio_origen", "ubicacion", "observado", "esperado", "explicacion", "requiere_revision_humana"])
        for a in alertas:
            w.writerow([a["id"], a["severidad"], a["regla"], a["criterio_origen"], a["clave"], a["observado"], a["esperado"],
                        a["explicacion"], "sí" if a["requiere_revision_humana"] else "no"])
    shutil.copy(RES / "reporte_entrega.md", d / "reporte_entrega.md")
    shutil.copy(RES / "tabla_comparativa.csv", d / "tabla_comparativa.csv")
    for f in ["fig1_recall_por_familia.png", "fig2_desempeno_global.png", "fig3_tiempo_ciclo.png"]:
        shutil.copy(RES / f, d / f)


def main():
    (WEB / "img").mkdir(parents=True, exist_ok=True)
    for f in ["fig1_recall_por_familia.png", "fig2_desempeno_global.png", "fig3_tiempo_ciclo.png"]:
        shutil.copy(RES / f, WEB / "img" / f)
    preparar_descargas()
    d = recolectar_datos()
    d["archivos"] = archivos_incrustados()
    datos = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    logo = "data:image/png;base64," + base64.b64encode((WEB / "img" / "unir.png").read_bytes()).decode()
    chartjs = (WEB / "vendor" / "chart.umd.js").read_text(encoding="utf-8")
    html = (PLANTILLA.replace("/*__DATOS__*/null", datos).replace("__LOGO__", logo)
            .replace("/*__CHARTJS__*/", chartjs.replace("</", "<\\/")))
    (WEB / "index.html").write_text(html, encoding="utf-8")
    print(f"Página generada en {WEB / 'index.html'}")


PLANTILLA = r"""<!DOCTYPE html>
<html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>QA agéntico para cálculos y tableros — TFM UNIR</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Montserrat:wght@600;700;800&display=swap" rel="stylesheet">
<style>
:root{--azul:#0367B3;--azul2:#1A77BD;--azul-claro:#E8F2FA;--azul-medio:#A9CEE9;--tinta:#0B0B0B;--gris:#4B5563;--gris2:#6B7280;--linea:#E5E7EB;--fondo:#F7F9FC;
--rojo:#C62828;--rojo-f:#FDECEC;--ambar:#B45309;--ambar-f:#FEF3E2;--verde:#15803D;--verde-f:#E7F6EC;--r:14px}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:76px}
body{margin:0;font-family:Inter,system-ui,sans-serif;color:var(--tinta);background:#fff;line-height:1.6;font-size:16px}
h1,h2,h3{font-family:Montserrat,Inter,sans-serif;line-height:1.2;margin:0}
h2{font-size:clamp(24px,3.2vw,34px);font-weight:800;margin-bottom:10px}h3{font-size:18px;font-weight:700}
.wrap{max-width:1160px;margin:0 auto;padding:0 22px}
section{padding:72px 0}section.alt{background:var(--fondo)}
.eyebrow{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--azul);margin-bottom:10px}
.lead{color:var(--gris);font-size:17px;max-width:760px;margin:0 0 28px}
/* barra superior */
header.top{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.94);backdrop-filter:saturate(1.4) blur(8px);border-bottom:1px solid var(--linea)}
.top .wrap{display:flex;align-items:center;gap:18px;height:66px}
.top img{height:38px;width:auto}.top .sep{width:1px;height:30px;background:var(--linea)}
.top .marca{white-space:nowrap;font-family:Montserrat,Inter,system-ui,sans-serif;font-weight:700;font-size:14px;line-height:1.2}.top .marca small{display:block;color:var(--gris2);font-weight:500;font-family:Inter;font-size:12px}
nav.menu{margin-left:auto;display:flex;gap:4px}
nav.menu a{white-space:nowrap;color:var(--tinta);text-decoration:none;font-size:14px;font-weight:500;padding:8px 11px;border-radius:8px}
nav.menu a:hover,nav.menu a.activo{background:var(--azul-claro);color:var(--azul)}
.hamb{display:none;margin-left:auto;background:none;border:1px solid var(--linea);border-radius:8px;padding:8px 10px;cursor:pointer}
/* portada */
.hero{padding:64px 0 56px;background:linear-gradient(180deg,#fff 0%,var(--azul-claro) 100%);position:relative;overflow:hidden}
.hero:after{content:"";position:absolute;right:-120px;top:-120px;width:420px;height:420px;border-radius:50%;border:60px solid rgba(3,103,179,.06)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}
.chip{font-size:12px;font-weight:600;padding:5px 11px;border-radius:999px;background:#fff;border:1px solid var(--azul-medio);color:var(--azul)}
.hero h1{font-size:clamp(28px,4.6vw,50px);font-weight:800;max-width:900px;letter-spacing:-.01em}
.hero h1 span{color:var(--azul)}
.hero p.sub{font-size:18px;color:var(--gris);max-width:780px;margin:18px 0 8px}
.autores{font-size:14px;color:var(--gris2);margin-bottom:34px}.autores b{color:var(--tinta)}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.kpi{background:#fff;border:1px solid var(--linea);border-radius:var(--r);padding:20px;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.kpi b{display:block;font-family:Montserrat,Inter,system-ui,sans-serif;font-size:36px;font-weight:800;color:var(--azul);line-height:1.1}
.kpi span{display:block;font-size:14px;color:var(--gris);margin-top:6px}
.kpi.neg b{color:var(--rojo)}
/* tarjetas y rejillas */
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:22px}.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.card{background:#fff;border:1px solid var(--linea);border-radius:var(--r);padding:22px}
.card p{color:var(--gris);font-size:15px;margin:8px 0 0}
.stat{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap}.stat b{font-family:Montserrat,Inter,system-ui,sans-serif;font-size:30px;color:var(--azul)}
.capa{border-top:4px solid var(--azul)}.capa .num{font-family:Montserrat,Inter,system-ui,sans-serif;font-weight:800;color:var(--azul-medio);font-size:34px;line-height:1}
.comp{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;padding:10px 0;border-top:1px solid var(--linea);font-size:14px}
.comp:first-of-type{border-top:0}
.badge{flex:none;font-size:11px;font-weight:700;padding:3px 8px;border-radius:999px;white-space:nowrap}
.b-ok{background:var(--verde-f);color:var(--verde)}.b-par{background:var(--ambar-f);color:var(--ambar)}.b-crit{background:var(--rojo-f);color:var(--rojo)}.b-alta{background:var(--ambar-f);color:var(--ambar)}.b-media{background:var(--azul-claro);color:var(--azul)}
.fam{border-left:4px solid var(--azul);border-radius:0;padding:14px 16px;background:#fff}
.fam h3{font-size:16px}.fam .n{font-family:Montserrat,Inter,system-ui,sans-serif;font-weight:800;font-size:26px;color:var(--azul)}
.fam ul{margin:8px 0 0;padding-left:18px;color:var(--gris);font-size:13px}
.fam.destacada{border-left-color:var(--rojo)}.fam.destacada .n{color:var(--rojo)}
/* controles */
.seg{display:inline-flex;flex-wrap:wrap;gap:6px;background:var(--fondo);border:1px solid var(--linea);padding:5px;border-radius:12px;margin-bottom:16px}
.seg button,.chipbtn{border:0;background:transparent;font:inherit;font-size:14px;font-weight:600;color:var(--gris);padding:8px 14px;border-radius:9px;cursor:pointer}
.seg button.on{background:#fff;color:var(--azul);box-shadow:0 1px 3px rgba(0,0,0,.08)}
.lienzo{position:relative;height:380px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:11px 12px;border-bottom:1px solid var(--linea);text-align:left;vertical-align:top}
thead th{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--gris2);font-weight:600;background:var(--fondo)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
tr.fw td{background:var(--azul-claro);font-weight:600}
.scroll{overflow-x:auto;border:1px solid var(--linea);border-radius:var(--r);background:#fff}
/* explorador de alertas */
.filtros{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:14px}
.filtros input,.filtros select{font:inherit;font-size:14px;padding:9px 12px;border:1px solid var(--linea);border-radius:10px;background:#fff}
.filtros input{flex:1;min-width:200px}
.chipbtn{border:1px solid var(--linea);background:#fff;padding:7px 12px;font-size:13px}
.chipbtn.on{border-color:var(--azul);color:var(--azul);background:var(--azul-claro)}
tr.fila{cursor:pointer}tr.fila:hover td{background:#FAFCFF}
tr.det td{background:var(--fondo);color:var(--gris);font-size:13px}
.pag{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:12px;font-size:14px;color:var(--gris)}
.btn{border:0;font:inherit;font-weight:600;font-size:14px;padding:10px 16px;border-radius:10px;cursor:pointer;background:var(--azul);color:#fff}
.btn:hover{background:#02579a}.btn.sec{background:#fff;color:var(--azul);border:1px solid var(--azul-medio)}.btn.rojo{background:var(--rojo)}.btn:disabled{opacity:.4;cursor:default}
/* simulador HITL */
.hitl{display:grid;grid-template-columns:1.3fr .7fr;gap:22px}
.alerta{border:1px solid var(--linea);border-radius:var(--r);padding:22px;background:#fff;min-height:250px}
.alerta .meta{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px;color:var(--gris2);margin-bottom:12px}
.alerta p.exp{font-size:16px;margin:0 0 14px}
.alerta .vals{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:18px}
.alerta .vals div{background:var(--fondo);border-radius:10px;padding:10px 12px;font-size:13px;color:var(--gris)}.alerta .vals b{display:block;color:var(--tinta);font-size:15px}
.acciones{display:flex;gap:10px;flex-wrap:wrap}
.barra{height:8px;background:var(--linea);border-radius:99px;overflow:hidden;margin:10px 0 16px}.barra i{display:block;height:100%;background:var(--azul);width:0;transition:width .3s}
.veredicto{border-radius:var(--r);padding:16px;font-weight:600;margin-top:12px}
/* gherkin */
.tabs{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
pre.gk{background:#0E1B2B;color:#DCE7F3;border-radius:var(--r);padding:18px;overflow:auto;font-size:13px;line-height:1.55;margin:0}
pre.gk .k{color:#7CC4FF;font-weight:600}pre.gk .c{color:#7F93A8}
.reglas{display:flex;flex-direction:column;gap:8px}
.regla{border:1px solid var(--linea);border-radius:10px;padding:10px 12px;font-size:14px;background:#fff}.regla b{color:var(--azul);margin-right:6px}
/* código */
pre.arbol{background:#fff;border:1px solid var(--linea);border-radius:var(--r);padding:18px;font-size:13px;overflow:auto;margin:0;line-height:1.6}
.cmd{display:flex;align-items:center;gap:10px;background:#0E1B2B;color:#DCE7F3;border-radius:10px;padding:10px 12px;margin-bottom:8px;font-family:ui-monospace,Consolas,monospace;font-size:13px}
.cmd code{flex:1;overflow:auto;white-space:nowrap}.cmd button{background:#1E3550;color:#fff;border:0;border-radius:7px;padding:5px 10px;font-size:12px;cursor:pointer}
.nota{background:var(--azul-claro);border-left:4px solid var(--azul);padding:14px 16px;border-radius:0 10px 10px 0;color:#1F3A56;font-size:14px}
.subir{display:flex;flex-direction:column;gap:12px}
.subir label{font-size:14px;font-weight:600}.subir input[type=file]{font:inherit;font-size:13px;padding:10px;border:1px dashed var(--azul-medio);border-radius:10px;background:var(--azul-claro);width:100%}
.descargas a{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--linea);border-radius:10px;text-decoration:none;color:var(--tinta);font-size:14px;margin-bottom:8px;background:#fff}
.descargas a:hover{border-color:var(--azul);color:var(--azul)}.descargas a span{font-size:12px;color:var(--gris2)}
.msg{font-size:13px;color:var(--rojo);min-height:18px}.ok{color:var(--verde)}
.resumen4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}
.resumen4 div{background:#fff;border:1px solid var(--linea);border-radius:12px;padding:14px}.resumen4 b{display:block;font-family:Montserrat,Inter,system-ui,sans-serif;font-size:24px;color:var(--azul)}.resumen4 span{font-size:13px;color:var(--gris)}
.reglaschips{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}.reglaschips span{font-size:12px;background:#fff;border:1px solid var(--linea);border-radius:999px;padding:5px 10px}
.si{color:var(--verde);font-weight:700}.no{color:var(--rojo);font-weight:700}
@media (max-width:980px){.resumen4{grid-template-columns:repeat(2,1fr)}}
footer{background:var(--tinta);color:#C9D1DB;padding:40px 0;font-size:14px}
footer .wrap{display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap;align-items:center}
footer img{height:34px;background:#fff;border-radius:8px;padding:6px 10px}
.vacio{padding:30px;text-align:center;color:var(--gris2)}
@media (max-width:980px){.kpis{grid-template-columns:repeat(2,1fr)}.grid3{grid-template-columns:1fr}.hitl{grid-template-columns:1fr}}
@media (max-width:1180px){nav.menu{display:none;position:absolute;top:66px;left:0;right:0;flex-direction:column;background:#fff;border-bottom:1px solid var(--linea);padding:10px 16px;box-shadow:0 8px 20px rgba(0,0,0,.06)}
 nav.menu.abierto{display:flex}.hamb{display:block}}
@media (max-width:860px){.grid2{grid-template-columns:1fr}.top .marca small{display:none}}
@media (max-width:520px){section{padding:52px 0}.kpis{grid-template-columns:1fr}.kpi b{font-size:30px}.top .sep,.top .marca{display:none}.lienzo{height:320px}.alerta .vals{grid-template-columns:1fr}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.barra i{transition:none}}
</style></head>
<body>
<header class="top"><div class="wrap">
 <img src="__LOGO__" alt="UNIR – La Universidad en Internet">
 <div class="sep"></div>
 <div class="marca">QA agéntico para cálculos y tableros<small>Trabajo Fin de Máster · Prototipo v1</small></div>
 <button class="hamb" id="hamb" aria-label="Abrir menú">☰</button>
 <nav class="menu" id="menu">
  <a href="#problema">Problema</a><a href="#arquitectura">Arquitectura</a><a href="#escenario">Escenario</a>
  <a href="#resultados">Resultados</a><a href="#alertas">Alertas</a><a href="#hitl">Revisión</a><a href="#probar">Probar</a><a href="#criterios">Criterios</a><a href="#codigo">Código</a>
 </nav>
</div></header>

<section class="hero" id="inicio"><div class="wrap">
 <div class="chips"><span class="chip">Máster en Transformación Digital · UNIR</span><span class="chip">Segunda entrega</span><span class="chip">Datos 100 % sintéticos</span></div>
 <h1>Validar cálculos y tableros <span>antes de la entrega</span>, con IA agéntica y machine learning</h1>
 <p class="sub">Un revisor automático que lee la intención del negocio (criterios Gherkin), la convierte en verificaciones y avisa qué está mal antes de que el informe llegue al cliente.</p>
 <div class="autores">Autores: <b>Nicolás Alfaro</b> y <b>Jinneth Tique Ortiz</b></div>
 <div class="kpis" id="kpis"></div>
</div></section>

<section id="problema"><div class="wrap">
 <span class="eyebrow">El problema · datos reales de Jira</span>
 <h2>El equipo dedica más horas a verificar que a construir</h2>
 <p class="lead">Hoy el QA replica a mano, en Excel o Python, los cálculos que ya hizo el ingeniero de datos, y revisa los tableros a ojo. Los registros de tiempo lo confirman.</p>
 <div class="grid2">
  <div class="card"><h3>Horas registradas por categoría</h3><div class="lienzo" style="height:300px"><canvas id="gJira"></canvas></div></div>
  <div style="display:flex;flex-direction:column;gap:16px" id="jiraStats"></div>
 </div>
</div></section>

<section class="alt" id="arquitectura"><div class="wrap">
 <span class="eyebrow">Arquitectura</span>
 <h2>Tres capas, de la intención del negocio a la decisión de entrega</h2>
 <p class="lead">El diseño objetivo (apartado 5.2) y lo que implementa este primer prototipo. Las etiquetas indican el estado de cada componente.</p>
 <div class="grid3">
  <div class="card capa"><div class="num">01</div><h3>Contexto</h3>
   <div class="comp"><span>Metadatos del pipeline y reglas de estilo del tablero</span><span class="badge b-ok">Implementado</span></div>
   <div class="comp"><span>Historias de usuario y criterios Gherkin</span><span class="badge b-ok">Implementado</span></div>
   <div class="comp"><span>Exposición a modelos vía MCP y RAG</span><span class="badge b-par">Siguiente entrega</span></div></div>
  <div class="card capa"><div class="num">02</div><h3>Núcleo de IA y ML</h3>
   <div class="comp"><span>Evaluador de reglas y relaciones metamórficas (R01–R11)</span><span class="badge b-par">v1 asistida por LLM</span></div>
   <div class="comp"><span>Detector de anomalías: Isolation Forest + LOF</span><span class="badge b-ok">Implementado</span></div>
   <div class="comp"><span>Auditor del tablero: valores, formato, títulos (T01–T03)</span><span class="badge b-par">v1 sobre metadatos</span></div></div>
  <div class="card capa"><div class="num">03</div><h3>Gobernanza (HITL)</h3>
   <div class="comp"><span>Alertas con severidad, criterio de origen y explicación</span><span class="badge b-ok">Implementado</span></div>
   <div class="comp"><span>Aprobación humana y reporte de entrega</span><span class="badge b-ok">Implementado</span></div>
   <div class="comp"><span>Alertas adaptativas con causa raíz</span><span class="badge b-par">Siguiente entrega</span></div></div>
 </div>
</div></section>

<section id="escenario"><div class="wrap">
 <span class="eyebrow">Escenario de prueba</span>
 <h2>Comercial Andina: una empresa ficticia con errores escondidos</h2>
 <p class="lead" id="escLead"></p>
 <div class="grid3" id="familias"></div>
</div></section>

<section class="alt" id="resultados"><div class="wrap">
 <span class="eyebrow">Resultados</span>
 <h2>Solo el framework detecta los errores de negocio</h2>
 <p class="lead">Comparación de cuatro métodos sobre las mismas anomalías. Ningún método ve la lista de errores; solo se usa al final para calificar.</p>
 <div class="seg" id="segGraf"><button data-g="familia" class="on">Detección por familia</button><button data-g="global">Precisión, recall y F1</button><button data-g="tiempo">Tiempo de ciclo</button></div>
 <div class="card"><div class="lienzo"><canvas id="gRes"></canvas></div></div>
 <div class="scroll" style="margin-top:18px"><table id="tablaRes"></table></div>
 <div class="card" style="margin-top:18px"><h3>Descarga los resultados del experimento</h3>
  <div class="descargas grid2" style="margin-top:12px;gap:0 14px">
   <a href="#" data-dl="alertas_experimento.csv">Alertas del experimento (CSV) <span>331 alertas · abre en Excel</span></a>
   <a href="#" data-dl="reporte_entrega.md">Reporte de entrega <span>decisión y alertas críticas</span></a>
   <a href="#" data-dl="tabla_comparativa.csv">Tabla comparativa (CSV) <span>4 métodos</span></a>
   <a href="#" data-dl="fig1_recall_por_familia.png">Gráfica: detección por familia <span>PNG</span></a>
   <a href="#" data-dl="fig2_desempeno_global.png">Gráfica: desempeño global <span>PNG</span></a>
   <a href="#" data-dl="fig3_tiempo_ciclo.png">Gráfica: tiempo de ciclo <span>PNG</span></a>
  </div>
  <p style="font-size:13px;color:var(--gris2);margin:6px 0 0">Los mismos archivos están en la carpeta <code>resultados/</code> del repositorio.</p>
 </div>
</div></section>

<section id="alertas"><div class="wrap">
 <span class="eyebrow">Explorador</span>
 <h2>Las alertas que emitió el framework</h2>
 <p class="lead">Cada alerta indica su severidad, el criterio de negocio que la originó y una explicación. Haz clic en una fila para ver el detalle.</p>
 <div class="filtros">
  <input id="fTexto" type="search" placeholder="Buscar por tienda, mes, regla o texto…" aria-label="Buscar alertas">
  <span id="fSev"></span>
  <select id="fCapa" aria-label="Capa"><option value="">Todas las capas</option><option value="tx">Transacciones</option><option value="kpi">KPIs</option><option value="total">Totales</option><option value="tab">Tablero</option></select>
 </div>
 <div class="scroll"><table><thead><tr><th>ID</th><th>Severidad</th><th>Regla</th><th>Dónde</th><th>Observado</th><th>Esperado</th></tr></thead><tbody id="tbAlertas"></tbody></table></div>
 <div class="pag"><span id="pagInfo"></span><span><button class="btn sec" id="pPrev">Anterior</button> <button class="btn sec" id="pNext">Siguiente</button></span></div>
</div></section>

<section class="alt" id="hitl"><div class="wrap">
 <span class="eyebrow">Compuerta humana · demostración</span>
 <h2>Tú decides: ¿se entrega o no?</h2>
 <p class="lead">Simulación en el navegador de la revisión humana de las alertas críticas. En el prototipo, esta revisión se hace con <code>src/revision_humana.py</code> y queda registrada.</p>
 <div class="hitl">
  <div class="alerta" id="hAlerta"></div>
  <div class="card"><h3>Avance de la revisión</h3><div class="barra"><i id="hBarra"></i></div>
   <div id="hResumen" style="font-size:14px;color:var(--gris)"></div>
   <div id="hVered"></div>
   <button class="btn sec" id="hReset" style="margin-top:14px">Reiniciar</button></div>
 </div>
</div></section>

<section id="probar"><div class="wrap">
 <span class="eyebrow">Prueba el modelo</span>
 <h2>Pon a prueba el revisor con el paquete de prueba o con tus propios datos</h2>
 <p class="lead">Descarga el paquete con 14 errores sembrados y documentados, cárgalo y compara lo que encuentra el revisor con la hoja de respuestas. Todo se procesa en tu navegador: los datos no salen de tu computador.</p>
 <div class="grid2">
  <div class="card"><h3>1. Descarga el paquete de prueba</h3>
   <div class="descargas" style="margin-top:12px">
    <a href="#" data-dl="prueba_transacciones.csv">prueba_transacciones.csv <span>1.241 filas · 11 errores</span></a>
    <a href="#" data-dl="prueba_kpis.csv">prueba_kpis.csv <span>5 KPIs · 3 errores</span></a>
    <a href="#" data-dl="prueba_casos_esperados.csv">prueba_casos_esperados.csv <span>hoja de respuestas</span></a>
    <a href="#" data-dl="LEEME_pruebas.txt">LEEME_pruebas.txt <span>instrucciones</span></a>
   </div>
   <p style="font-size:13px;color:var(--gris2);margin:6px 0 0">Abre los CSV en Excel, modifícalos (corrige casos o crea errores nuevos), guárdalos como CSV y súbelos en el paso 2. Este paquete es independiente del experimento principal: sus resultados no cambian.</p>
  </div>
  <div class="card subir"><h3>2. Carga los archivos y ejecuta</h3>
   <label for="upTx">Transacciones (CSV, obligatorio)</label><input type="file" id="upTx" accept=".csv,text/csv">
   <label for="upKp">KPIs publicados (CSV, opcional: activa las reglas R03, R05 y R06)</label><input type="file" id="upKp" accept=".csv,text/csv">
   <div class="acciones"><button class="btn" id="btnRun">Ejecutar revisión</button><button class="btn sec" id="btnDemo">Usar datos de prueba</button></div>
   <div class="msg" id="pMsg"></div>
  </div>
 </div>
 <div class="card" style="margin-top:18px"><h3>Reglas predefinidas que se aplican</h3>
  <div class="reglaschips"><span><b>R01</b> ingreso = unidades × precio × (1 − descuento)</span><span><b>R02</b> sin valores negativos, vacíos ni descuentos fuera de 0–50 %</span><span><b>R04</b> tiendas pequeñas cerradas el domingo</span><span><b>R08</b> sin transacciones duplicadas</span><span><b>EST</b> detección estadística de picos (versión ligera del ML)</span><span><b>R03</b> ingreso mensual = suma por fecha de factura</span><span><b>R05</b> margen = (ingreso − costo) / ingreso</span><span><b>R06</b> margen entre 0 % y 60 %</span></div>
  <p style="font-size:13px;color:var(--gris2);margin:10px 0 0">Columnas esperadas: fecha_factura, tienda, tamano, producto, precio_lista, unidades, descuento, ingreso y costo (o costo_unitario). Acepta CSV separados por coma o por punto y coma.</p>
 </div>
 <div id="pRes"></div>
 <div class="card" style="margin-top:22px" id="pHistCard"><div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap"><h3>Historial de pruebas</h3><button class="btn sec" id="hBorrar">Borrar historial</button></div>
  <p style="font-size:13px;color:var(--gris2);margin:4px 0 12px">Cada revisión que ejecutes queda guardada en este navegador (hasta 20), aunque cierres o recargues la página. No se envía a ningún servidor.</p>
  <div id="pHist"></div></div>
</div></section>

<section id="criterios"><div class="wrap">
 <span class="eyebrow">Trazabilidad</span>
 <h2>De cada criterio Gherkin a una regla ejecutable</h2>
 <p class="lead">Así se lee la intención del negocio. Cada escenario se convierte en una regla, y cada alerta puede rastrearse hasta aquí.</p>
 <div class="tabs seg" id="tabsGk"></div>
 <div class="grid2"><pre class="gk" id="gkTexto"></pre><div class="reglas" id="gkReglas"></div></div>
</div></section>

<section class="alt" id="codigo"><div class="wrap">
 <span class="eyebrow">Código fuente y ejecución</span>
 <h2>Reproducible con dos comandos</h2>
 <p class="lead">Python 3.11+, librerías de código abierto y semillas fijas: cualquier persona obtiene los mismos datos y métricas.</p>
 <div class="grid2">
  <pre class="arbol">qa-agentico/
├── AGENTS.md · README.md · requirements.txt
├── contexto/            ← intención del negocio
│   ├── criterios/*.feature   (13 escenarios Gherkin)
│   ├── historias_usuario.md
│   ├── pipeline.yaml         (definición de KPIs)
│   ├── estilo_tablero.yaml   (formato y títulos)
│   └── linea_base_jira.yaml  (horas reales)
├── src/                 ← código
│   ├── generador_datos.py · inyector_anomalias.py
│   ├── generar_escenario.py
│   ├── metodos_clasicos.py   (Pandera, PyOD)
│   ├── framework_agentico.py (evaluador, auditor, alertas)
│   ├── revision_humana.py    (compuerta HITL)
│   ├── evaluar.py · generar_pagina.py
├── datos/               ← escenario generado
├── resultados/          ← métricas, alertas, gráficas
├── docs/                ← texto de avance del TFM
└── web/                 ← esta página</pre>
  <div>
   <div class="cmd"><code>pip install -r requirements.txt</code><button data-c="pip install -r requirements.txt">Copiar</button></div>
   <div class="cmd"><code>python src/generar_escenario.py</code><button data-c="python src/generar_escenario.py">Copiar</button></div>
   <div class="cmd"><code>python src/evaluar.py</code><button data-c="python src/evaluar.py">Copiar</button></div>
   <div class="cmd"><code>python src/revision_humana.py</code><button data-c="python src/revision_humana.py">Copiar</button></div>
   <p id="repoBox" style="margin:16px 0"></p>
   <div class="nota"><b>Alcance de la v1.</b> Las reglas del evaluador se generaron con un modelo de lenguaje en modo asistido y corren como código determinista. Los tiempos del QA manual dentro del experimento son supuestos conservadores (11 h por ciclo frente a 33 h de mediana real por ticket). Los agentes con LLM en ejecución, MCP/RAG y el auditor multimodal corresponden a la siguiente entrega.</div>
  </div>
 </div>
</div></section>

<footer><div class="wrap">
 <div><img src="__LOGO__" alt="UNIR"></div>
 <div>Nicolás Alfaro y Jinneth Tique Ortiz · Máster en Transformación Digital, UNIR · 2026<br>
 Trabajo académico. Datos 100 % sintéticos de una empresa ficticia; sin datos personales ni de clientes.<br>
 Desarrollado con apoyo de asistentes de IA, con dirección y validación de los autores.</div>
</div></footer>

<script>/*__CHARTJS__*/</script>
<script>
const D = /*__DATOS__*/null;
if (window.Chart) { Chart.defaults.locale = "es-CO"; Chart.defaults.font.family = "Inter, system-ui, sans-serif"; }
const fmtV = v => { const x = Number(v); if (v === "" || isNaN(x)) return v;
 if (Math.abs(x) >= 1000) return "$ " + Math.round(x).toLocaleString("es-CO");
 if (Math.abs(x) < 1 && x !== 0) return (x*100).toFixed(1).replace(".", ",") + " %"; return String(v).replace(".", ","); };
const M = D.m.metodos, E = D.m.escenario;
const FAM = [["datos","Datos"],["contextual","Contextual"],["calculo","Cálculo"],["semantica","Semántica"],["visualizacion","Visualización"]];
const MET = Object.keys(M), COL = ["#9CA3AF","#E0A458","#5B9A7D","#0367B3"];
const pct = x => Math.round(x*100) + " %", n2 = x => x.toFixed(2).replace(".", ","), miles = x => Math.round(x).toLocaleString("es-CO");
const $ = s => document.querySelector(s), el = (t, a={}, h="") => Object.assign(document.createElement(t), a, h ? {innerHTML:h} : {});
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

/* menú móvil y sección activa */
$("#hamb").onclick = () => $("#menu").classList.toggle("abierto");
document.querySelectorAll("#menu a").forEach(a => a.onclick = () => $("#menu").classList.remove("abierto"));
const obs = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) document.querySelectorAll("#menu a").forEach(a => a.classList.toggle("activo", a.getAttribute("href") === "#" + e.target.id)); }), {rootMargin:"-45% 0px -50% 0px"});
document.querySelectorAll("section[id]").forEach(s => obs.observe(s));

/* indicadores principales */
const fw = M["Framework agéntico"], man = M["Manual (simulado)"], jq = D.jira.categorias[0];
[[pct(fw.recall), `de los ${E.anomalias} errores detectados antes de la entrega (${fw.TP} de ${E.anomalias})`],
 [pct(fw.recall_semantica), "de los errores semánticos y del tablero detectados; las reglas genéricas y el ML: 0 %"],
 ["−" + Math.round(D.m.reduccion_tiempo_pct) + " %", `tiempo de ciclo de QA estimado (${man.horas_ciclo.toFixed(0)} h → ${fw.horas_ciclo.toFixed(1).replace(".",",")} h)`],
 [String(jq.pct_total).replace(".",",") + " %", "de las horas reales del proyecto se van en QA operativo (Jira)", "neg"]
].forEach(([v,t,c]) => $("#kpis").append(el("div",{className:"kpi "+(c||"")},`<b>${v}</b><span>${t}</span>`)));

/* Jira */
const cats = D.jira.categorias;
if (!window.Chart) { const mx = Math.max(...cats.map(c=>c.horas));
 $("#gJira").parentNode.innerHTML = cats.map((c,i) => `<div style="margin:10px 0;font-size:13px"><div style="display:flex;justify-content:space-between"><span>${esc(c.nombre)}</span><b>${miles(c.horas)} h · ${String(c.pct_total).replace(".",",")} %</b></div><div style="height:12px;background:var(--linea);border-radius:6px;overflow:hidden"><i style="display:block;height:100%;width:${c.horas/mx*100}%;background:${i===0?"#C62828":i===3?"#E57373":"#A9CEE9"}"></i></div></div>`).join("");
} else new Chart($("#gJira"), {type:"bar", data:{labels:cats.map(c=>c.nombre), datasets:[{data:cats.map(c=>c.horas), backgroundColor:cats.map((c,i)=>i===0?"#C62828":i===3?"#E57373":"#A9CEE9"), borderRadius:6}]},
 options:{indexAxis:"y", maintainAspectRatio:false, plugins:{legend:{display:false}, tooltip:{callbacks:{label:c=>` ${miles(c.raw)} h · ${String(cats[c.dataIndex].pct_total).replace(".",",")} % del total`}}},
  scales:{x:{grid:{color:"#EEF2F6"}, title:{display:true,text:"Horas registradas"}}, y:{grid:{display:false}}}}});
const ing = cats[1];
$("#jiraStats").innerHTML = `
 <div class="card"><div class="stat"><b>${String(jq.pct_total).replace(".",",")} %</b><span>de ${miles(D.jira.total_horas)} h totales son de QA operativo (${miles(jq.horas)} h). Con la gestión de QA llega a ${String((jq.pct_total+cats[3].pct_total).toFixed(1)).replace(".",",")} %.</span></div></div>
 <div class="card"><div class="stat"><b>${String(jq.promedio_ticket_h).replace(".",",")} h</b><span>promedio por ticket de QA (mediana ${String(jq.mediana_ticket_h).replace(".",",")} h, máximo ${String(jq.maximo_ticket_h).replace(".",",")} h)</span></div></div>
 <div class="card"><div class="stat"><b>${(jq.horas/ing.horas).toFixed(1).replace(".",",")}×</b><span>más horas en QA operativo que en ingeniería de datos, que es quien construye</span></div></div>`;

/* escenario */
$("#escLead").textContent = `${miles(E.transacciones)} transacciones de 10 tiendas y 8 productos durante seis meses, ${E.celdas_kpi} KPIs mensuales y un tablero con ${E.valores_tablero} valores. Les inyectamos ${E.anomalias} errores en cinco familias.`;
const nomFam = Object.fromEntries(FAM);
FAM.forEach(([k,nom]) => { const f = D.familias[k]||{}, tot = Object.values(f).reduce((a,b)=>a+b.n,0);
 const d = el("div",{className:"card fam"+(k==="semantica"||k==="visualizacion"?" destacada":"")},
  `<div style="display:flex;justify-content:space-between;align-items:baseline"><h3>${nom}</h3><span class="n">${tot}</span></div><ul>${Object.entries(f).map(([t,v])=>`<li><b>${t}</b> ${esc(v.ej)} (${v.n})</li>`).join("")}</ul>`);
 $("#familias").append(d); });

/* resultados */
let gRes;
function grafica(tipo){
 if (!window.Chart) { const img = {familia:"fig1_recall_por_familia.png", global:"fig2_desempeno_global.png", tiempo:"fig3_tiempo_ciclo.png"}[tipo];
  $("#gRes").parentNode.innerHTML = `<canvas id="gRes" style="display:none"></canvas><img src="data:image/png;base64,${D.archivos[img].b64}" alt="Gráfica de resultados" style="width:100%;height:100%;object-fit:contain">`; return; }
 if (gRes) gRes.destroy();
 let cfg;
 if (tipo==="familia") cfg = {labels:FAM.map(f=>f[1]), ds:MET.map((m,i)=>({label:m,data:FAM.map(([k])=>M[m]["recall_"+k]*100),backgroundColor:COL[i],borderRadius:5})), y:"% de errores detectados", max:100};
 else if (tipo==="global") cfg = {labels:["Precisión","Recall","F1"], ds:MET.map((m,i)=>({label:m,data:[M[m].precision,M[m].recall,M[m].f1],backgroundColor:COL[i],borderRadius:5})), y:"Valor (0 a 1)", max:1};
 else cfg = {labels:["QA manual (simulado)","Framework + revisión humana"], ds:[{label:"Horas por ciclo",data:[man.horas_ciclo,fw.horas_ciclo],backgroundColor:[COL[0],COL[3]],borderRadius:6}], y:"Horas por ciclo de QA"};
 gRes = new Chart($("#gRes"), {type:"bar", data:{labels:cfg.labels, datasets:cfg.ds},
  options:{maintainAspectRatio:false, plugins:{legend:{display:cfg.ds.length>1, position:"bottom"}}, scales:{y:{beginAtZero:true, max:cfg.max, title:{display:true,text:cfg.y}, grid:{color:"#EEF2F6"}}, x:{grid:{display:false}}}}});
}
document.querySelectorAll("#segGraf button").forEach(b => b.onclick = () => { document.querySelectorAll("#segGraf button").forEach(x=>x.classList.remove("on")); b.classList.add("on"); grafica(b.dataset.g); });
grafica("familia");
$("#tablaRes").innerHTML = `<thead><tr><th>Método</th><th class="n">Precisión</th><th class="n">Recall</th><th class="n">F1</th>${FAM.map(f=>`<th class="n">${f[1]}</th>`).join("")}<th class="n">Horas</th></tr></thead><tbody>` +
 MET.map(m=>`<tr class="${m==="Framework agéntico"?"fw":""}"><td>${m}</td><td class="n">${n2(M[m].precision)}</td><td class="n">${n2(M[m].recall)}</td><td class="n">${n2(M[m].f1)}</td>${FAM.map(([k])=>`<td class="n">${pct(M[m]["recall_"+k])}</td>`).join("")}<td class="n">${M[m].horas_ciclo.toFixed(1).replace(".",",")}</td></tr>`).join("") + "</tbody>";

/* explorador de alertas */
const SEV = ["crítica","alta","media"], clsSev = {"crítica":"b-crit","alta":"b-alta","media":"b-media"};
const donde = c => { const p = c.split("|"); return p[0]==="tx" ? `Transacción #${p[1]}` : p[0]==="kpi" ? `KPI ${p[1]} · ${p[2]}` : p[0]==="total" ? `Total compañía · ${p[1]}` : `Tablero ${p[1]} · ${p[2]} · ${p[3]}`; };
let sevOn = new Set(SEV), pag = 0, abierta = null; const PP = 12;
SEV.forEach(s => { const b = el("button",{className:"chipbtn on",textContent:`${s} (${D.alertas.filter(a=>a.severidad===s).length})`}); b.onclick=()=>{ sevOn.has(s)?sevOn.delete(s):sevOn.add(s); b.classList.toggle("on"); pag=0; pintar(); }; $("#fSev").append(b); });
function filtradas(){ const q = $("#fTexto").value.toLowerCase(), cp = $("#fCapa").value;
 return D.alertas.filter(a => sevOn.has(a.severidad) && (!cp || a.clave.startsWith(cp+"|")) && (!q || (a.id+a.regla+a.clave+a.explicacion+a.criterio_origen).toLowerCase().includes(q))); }
function pintar(){ const f = filtradas(), tot = Math.max(1, Math.ceil(f.length/PP)); pag = Math.min(pag, tot-1);
 const tb = $("#tbAlertas"); tb.innerHTML = "";
 if (!f.length) { tb.innerHTML = `<tr><td colspan="6" class="vacio">No hay alertas con esos filtros.</td></tr>`; }
 f.slice(pag*PP, pag*PP+PP).forEach(a => {
  const tr = el("tr",{className:"fila"},`<td>${a.id}</td><td><span class="badge ${clsSev[a.severidad]}">${a.severidad}</span></td><td>${a.regla}</td><td>${esc(donde(a.clave))}</td><td>${esc(fmtV(a.observado))}</td><td>${esc(fmtV(a.esperado))}</td>`);
  tr.onclick = () => { abierta = abierta===a.id ? null : a.id; pintar(); }; tb.append(tr);
  if (abierta===a.id) tb.append(el("tr",{className:"det"},`<td colspan="6"><b>Criterio de origen:</b> ${esc(a.criterio_origen)}<br>${esc(a.explicacion)}<br><b>Requiere revisión humana:</b> ${a.requiere_revision_humana?"sí":"no"}</td>`));
 });
 $("#pagInfo").textContent = `${f.length} alertas · página ${pag+1} de ${tot}`; $("#pPrev").disabled = pag===0; $("#pNext").disabled = pag>=tot-1; }
$("#fTexto").oninput = () => { pag=0; pintar(); }; $("#fCapa").onchange = () => { pag=0; pintar(); };
$("#pPrev").onclick = () => { pag--; pintar(); }; $("#pNext").onclick = () => { pag++; pintar(); };
pintar();

/* simulador de revisión humana */
const crit = D.alertas.filter(a => a.severidad==="crítica"); let hi = 0, dec = [];
function hPintar(){
 $("#hBarra").style.width = (hi/crit.length*100) + "%";
 const ap = dec.filter(d=>d==="a").length, re = dec.filter(d=>d==="r").length;
 $("#hResumen").innerHTML = `Revisadas <b>${hi}</b> de ${crit.length} alertas críticas · confirmadas <b>${ap}</b> · descartadas <b>${re}</b>`;
 if (hi < crit.length) { const a = crit[hi];
  $("#hAlerta").innerHTML = `<div class="meta"><span class="badge b-crit">crítica</span><span>${a.id}</span><span>·</span><span>${a.regla}</span><span>·</span><span>${esc(a.criterio_origen)}</span></div>
   <p class="exp">${esc(a.explicacion)}</p><div class="vals"><div>Valor observado<b>${esc(fmtV(a.observado))}</b></div><div>Valor esperado<b>${esc(fmtV(a.esperado))}</b></div></div>
   <div class="acciones"><button class="btn rojo" id="hA">Confirmar error</button><button class="btn sec" id="hR">Descartar (falso positivo)</button></div>`;
  $("#hA").onclick = () => { dec.push("a"); hi++; hPintar(); }; $("#hR").onclick = () => { dec.push("r"); hi++; hPintar(); };
  $("#hVered").innerHTML = "";
 } else {
  $("#hAlerta").innerHTML = `<div class="vacio"><h3>Revisión terminada</h3><p>Revisaste las ${crit.length} alertas críticas.</p></div>`;
  $("#hVered").innerHTML = ap ? `<div class="veredicto" style="background:var(--rojo-f);color:var(--rojo)">No entregar: hay ${ap} errores confirmados por corregir.</div>`
                              : `<div class="veredicto" style="background:var(--verde-f);color:var(--verde)">Se puede entregar: no quedan errores críticos confirmados.</div>`;
 } }
$("#hReset").onclick = () => { hi=0; dec=[]; hPintar(); }; hPintar();


/* ===== prueba del modelo con CSV ===== */
function leerCSV(txt){
 txt = txt.replace(/^﻿/, "").replace(/\r/g, "");
 const lineas = txt.split("\n").filter(l => l.trim());
 const sep = (lineas[0].match(/;/g)||[]).length > (lineas[0].match(/,/g)||[]).length ? ";" : ",";
 const cab = lineas[0].split(sep).map(h => h.trim().toLowerCase());
 return {cab, filas: lineas.slice(1).map(l => { const v = l.split(sep), o = {};
  cab.forEach((h,i) => { let x = (v[i]||"").trim(); if (sep===";") x = x.replace(/\./g,"").replace(",","."); o[h] = x; }); return o; })};
}
const num = x => (x === "" || x === undefined) ? NaN : Number(x);
const SEVP = {"crítica":3, "alta":2, "media":1};
const MESES = {ene:1,feb:2,mar:3,abr:4,may:5,jun:6,jul:7,ago:8,sep:9,sept:9,oct:10,nov:11,dic:12,jan:1,apr:4,aug:8,dec:12};
function leerFecha(t){ t = String(t||"").trim().split(/[ T]/)[0]; let m;
 if ((m = t.match(/^(\d{4})[-\/](\d{1,2})[-\/](\d{1,2})$/))) return new Date(+m[1], m[2]-1, +m[3]);
 if ((m = t.match(/^(\d{1,2})[-\/](\d{1,2})[-\/](\d{2,4})$/))) { const a = m[3].length === 2 ? 2000 + +m[3] : +m[3]; return new Date(a, m[2]-1, +m[1]); }
 return null; }
const anioMes = d => d ? d.getFullYear() + "-" + String(d.getMonth()+1).padStart(2,"0") : "";
function leerMes(t){ t = String(t||"").trim().toLowerCase(); let m;
 if ((m = t.match(/^(\d{4})[-\/](\d{1,2})$/))) return m[1] + "-" + m[2].padStart(2,"0");
 if ((m = t.match(/^([a-z]{3,4})\.?[-\/ ](\d{2,4})$/)) && MESES[m[1]]) return (m[2].length === 2 ? "20" + m[2] : m[2]) + "-" + String(MESES[m[1]]).padStart(2,"0");
 return anioMes(leerFecha(t)); }
function revisar(txTxt, kpTxt){
 const T = leerCSV(txTxt), falta = ["fecha_factura","tienda","producto","precio_lista","unidades","descuento","ingreso"].filter(c => !T.cab.includes(c));
 if (falta.length) throw new Error("Al archivo de transacciones le faltan columnas: " + falta.join(", "));
 const al = [], add = (sev, regla, ubic, obs, esp, det) => al.push({sev, regla, ubic, obs, esp, det});
 const vistos = {}, grupos = {}; let malasFechas = 0;
 T.filas.forEach((r,i) => {
  const id = r.id_transaccion || ("fila " + (i+2)), u = num(r.unidades), p = num(r.precio_lista), d = num(r.descuento), ing = num(r.ingreso);
  const esp = u*p*(1-d);
  if (!isNaN(ing) && isFinite(esp) && Math.abs(ing - esp) > 0.01) add("alta","R01",id,fmtV(ing),fmtV(esp),"el ingreso no corresponde a unidades × precio × (1 − descuento)");
  if (isNaN(ing) || ing < 0 || u < 0 || d < 0 || d > 0.5) add("alta","R02",id, isNaN(ing) ? "ingreso vacío" : `unidades ${u} · descuento ${d}`, "valores válidos","valor inválido (negativo, vacío o descuento fuera de 0–50 %)");
  const f = leerFecha(r.fecha_factura); if (!f) malasFechas++;
  if ((r.tamano||"").toLowerCase().startsWith("peque") && f && f.getDay() === 0 && u !== 0) add("alta","R04",id,`${u} unidades`,"0 (cerrada)","venta registrada en domingo en una tienda pequeña");
  const k = anioMes(f) + String(f ? f.getDate() : r.fecha_factura) + "|" + r.tienda + "|" + r.producto; (vistos[k] = vistos[k] || []).push(id);
  const g = r.tienda + "|" + r.producto; (grupos[g] = grupos[g] || []).push({id, u: Math.max(0, u||0)});
 });
 Object.values(vistos).filter(v => v.length > 1).forEach(v => v.forEach(id => add("alta","R08",id,"repetida",`única (${v.join(", ")})`,"combinación fecha de factura + tienda + producto duplicada")));
 const med = a => { const s = [...a].sort((x,y)=>x-y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m-1]+s[m])/2; };
 Object.values(grupos).forEach(gr => { const us = gr.map(x=>x.u), m = med(us), mad = med(us.map(x=>Math.abs(x-m)));
  gr.forEach(x => { const z = (x.u - m)/(mad + 1); if (z >= 8) add("media","EST",x.id,`${x.u} unidades`,`≈ ${Math.round(m)} habituales`,"pico de unidades muy por encima de lo habitual para esa tienda y producto"); }); });
 if (kpTxt){
  const K = leerCSV(kpTxt), rec = {}; var kpSinCruce = 0;
  T.filas.forEach(r => { const k = r.tienda + "|" + anioMes(leerFecha(r.fecha_factura)), ing = num(r.ingreso);
   const costo = !isNaN(num(r.costo)) ? num(r.costo) : num(r.unidades) * num(r.costo_unitario);
   const mg = T.cab.includes("margen") ? num(r.margen) : ing - costo;
   rec[k] = rec[k] || {ing:0, costo:0, mg:0}; if (!isNaN(ing)) rec[k].ing += ing; if (!isNaN(costo)) rec[k].costo += costo; if (!isNaN(mg)) rec[k].mg += mg; });
  K.filas.forEach(r => { const mes = leerMes(r.mes), k = r.tienda + "|" + mes, e = rec[k], ubic = r.tienda + " | " + mes; if (!e) { kpSinCruce++; return; }
   const it = num(r.ingreso_total), mp = num(r.margen_pct), me = e.mg / e.ing; /* misma definición que el pipeline: margen_total / ingreso_total */
   if (!isNaN(it) && Math.abs(it - e.ing) > 1) add("crítica","R03",ubic,fmtV(it),fmtV(e.ing),"el ingreso mensual publicado no coincide con la suma por fecha de factura");
   if (!isNaN(mp) && isFinite(me) && Math.abs(mp - me) > 0.0005) add("crítica","R05",ubic,fmtV(mp),fmtV(me),"el margen publicado no corresponde a (ingreso − costo) / ingreso");
   if (!isNaN(mp) && (mp < 0 || mp > 0.6)) add("alta","R06",ubic,fmtV(mp),"0 % – 60 %","margen fuera del rango razonable"); });
 }
 al.sort((a,b) => SEVP[b.sev] - SEVP[a.sev]);
 const avisos = [];
 if (malasFechas) avisos.push(`${malasFechas} filas tienen una fecha_factura que no se pudo leer (use AAAA-MM-DD o DD/MM/AAAA).`);
 if (kpTxt && typeof kpSinCruce !== "undefined" && kpSinCruce) avisos.push(`${kpSinCruce} KPIs no coinciden con ninguna tienda y mes de las transacciones.`);
 return {al, n: T.filas.length, avisos, conIds: T.cab.includes("id_transaccion"), conKpis: !!kpTxt};
}
let ultimo = null;
function mostrar(res, conCasos, opcSinScroll){
 ultimo = res; const c = s => res.al.filter(a => a.sev === s).length, crit = c("crítica");
 let html = `<div class="resumen4"><div><b>${res.n.toLocaleString("es-CO")}</b><span>transacciones analizadas</span></div><div><b>${crit}</b><span>alertas críticas</span></div><div><b>${c("alta")}</b><span>alertas altas</span></div><div><b>${c("media")}</b><span>alertas medias (estadística)</span></div></div>`;
 html += (crit + c("alta")) ? `<div class="veredicto" style="background:var(--rojo-f);color:var(--rojo)">Decisión sugerida: no entregar hasta revisar ${crit + c("alta")} alertas críticas y altas.</div>`
                            : `<div class="veredicto" style="background:var(--verde-f);color:var(--verde)">Decisión sugerida: se puede entregar; no hay alertas críticas ni altas.</div>`;
 if (res.avisos && res.avisos.length) html += `<div class="nota" style="margin-top:12px;border-left-color:var(--ambar);background:var(--ambar-f);color:#7A3E06">${res.avisos.map(esc).join("<br>")}</div>`;
 if (D.pruebas && (conCasos || res.conIds)){
  const ok = D.pruebas.casos.map(cs => { const enKpi = cs.archivo === "prueba_kpis.csv";
   if (enKpi && !res.conKpis) return {cs, est:"Sin evaluar"};
   return {cs, est: res.al.some(a => cs.ubicacion.split(" y ").some(u => a.ubic === u.trim())) ? "Sí" : "No"}; });
  const det = ok.filter(o => o.est === "Sí").length, ev = ok.filter(o => o.est !== "Sin evaluar").length; res.casos = det + " de " + ev;
  html += `<h3 style="margin:22px 0 4px">Comparación con la hoja de respuestas: ${det} de ${ev} casos detectados</h3>` +
   (conCasos ? "" : `<p style="font-size:13px;color:var(--gris2);margin:0 0 8px">Su archivo fue modificado: si corrigió alguno de los casos originales, es normal que aparezca como "No". Los errores nuevos que haya creado aparecen en la lista de alertas.</p>`) +
   `<div class="scroll"><table><thead><tr><th>Caso</th><th>Tipo</th><th>Ubicación</th><th>Error sembrado</th><th>Regla esperada</th><th>¿Detectado?</th></tr></thead><tbody>` +
   ok.map(o => `<tr><td>${o.cs.caso}</td><td>${esc(o.cs.tipo)}</td><td>${esc(o.cs.ubicacion)}</td><td>${esc(o.cs.descripcion)}</td><td>${esc(o.cs.regla_que_debe_detectarlo)}</td><td class="${o.est==="Sí"?"si":o.est==="No"?"no":""}">${o.est}</td></tr>`).join("") + `</tbody></table></div>`;
 }
 html += `<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin:22px 0 8px"><h3>Alertas emitidas (${res.al.length})</h3><span class="acciones"><button class="btn sec" id="btnExp">Exportar CSV</button><button class="btn sec" id="btnCop">Copiar CSV</button></span></div>
  <div class="scroll" style="max-height:460px;overflow:auto"><table><thead><tr><th>Severidad</th><th>Regla</th><th>Ubicación</th><th>Observado</th><th>Esperado</th><th>Explicación</th></tr></thead><tbody>` +
  (res.al.length ? res.al.map(a => `<tr><td><span class="badge ${clsSev[a.sev]}">${a.sev}</span></td><td>${a.regla}</td><td>${esc(a.ubic)}</td><td>${esc(a.obs)}</td><td>${esc(a.esp)}</td><td>${esc(a.det)}</td></tr>`).join("") : `<tr><td colspan="6" class="vacio">Sin alertas.</td></tr>`) + `</tbody></table></div>`;
 $("#pRes").innerHTML = html;
 const csvTxt = () => ["severidad;regla;ubicacion;observado;esperado;explicacion"].concat(res.al.map(a => [a.sev,a.regla,a.ubic,a.obs,a.esp,a.det].map(x => String(x).replace(/;/g,",")).join(";"))).join("\n");
 $("#btnExp").onclick = () => { try { const u = URL.createObjectURL(new Blob(["﻿" + csvTxt()], {type:"text/csv"})), a = el("a",{href:u, download:"alertas_revision.csv"}); document.body.append(a); a.click(); a.remove(); } catch(e) { $("#pMsg").textContent = "La descarga no está disponible aquí; usa Copiar CSV."; } };
 $("#btnCop").onclick = async () => { try { await navigator.clipboard.writeText(csvTxt()); $("#btnCop").textContent = "Copiado"; } catch(e) { $("#btnCop").textContent = "No se pudo copiar"; } setTimeout(() => $("#btnCop").textContent = "Copiar CSV", 1500); };
 if (!opcSinScroll) $("#pRes").scrollIntoView({behavior:"smooth", block:"start"});
}
const leerArchivo = f => new Promise((ok, mal) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = mal; r.readAsText(f, "utf-8"); });
$("#btnRun").onclick = async () => { const m = $("#pMsg"); m.className = "msg";
 const ft = $("#upTx").files[0], fk = $("#upKp").files[0];
 if (!ft) { m.textContent = "Primero carga el archivo de transacciones (o usa los datos de prueba)."; return; }
 try { const tx = await leerArchivo(ft), kp = fk ? await leerArchivo(fk) : null;
  const res = revisar(tx, kp), igual = !!(D.pruebas && tx.replace(/\r/g,"") === D.pruebas.tx.replace(/\r/g,""));
  m.className = "msg ok"; m.textContent = `Revisión completada: ${res.al.length} alertas. Quedó guardada en el historial.`;
  mostrar(res, igual); guardarH(ft.name + (fk ? " + " + fk.name : ""), res, igual); }
 catch(e) { m.textContent = e.message; } };
$("#upTx").onchange = () => { $("#pMsg").textContent = ""; };
$("#btnDemo").onclick = () => { if (!D.pruebas) return; const res = revisar(D.pruebas.tx, D.pruebas.kpis);
 $("#pMsg").className = "msg ok"; $("#pMsg").textContent = `Datos de prueba cargados: ${res.al.length} alertas. Quedó guardada en el historial.`; mostrar(res, true); guardarH("Paquete de prueba (sin modificar)", res, true); };


/* historial de pruebas: se guarda solo en este navegador */
const CLAVE_H = "qa_agentico_historial_v1";
const leerH = () => { try { return JSON.parse(localStorage.getItem(CLAVE_H) || "[]"); } catch(e) { return []; } };
const escribirH = h => { try { localStorage.setItem(CLAVE_H, JSON.stringify(h.slice(0,20))); return true; } catch(e) { return false; } };
function guardarH(origen, res, conCasos){
 const c = s => res.al.filter(a => a.sev === s).length;
 const h = leerH(); h.unshift({fecha: new Date().toLocaleString("es-CO"), origen, n: res.n, crit: c("crítica"), alta: c("alta"), media: c("media"),
  casos: res.casos || "—", decision: (c("crítica") + c("alta")) ? "No entregar" : "Entregar", conCasos, res: {al: res.al, n: res.n, avisos: res.avisos, conIds: res.conIds, conKpis: res.conKpis}});
 if (!escribirH(h)) $("#pHist").dataset.aviso = "Este navegador no permite guardar el historial; las pruebas se verán solo mientras la página esté abierta.";
 pintarH(h);
}
let hMem = [];
function pintarH(h){
 h = h || leerH(); if (!h.length && hMem.length) h = hMem; hMem = h;
 const aviso = $("#pHist").dataset.aviso ? `<p class="msg">${$("#pHist").dataset.aviso}</p>` : "";
 if (!h.length) { $("#pHist").innerHTML = aviso + `<div class="vacio">Aún no hay pruebas guardadas. Ejecuta una revisión para empezar.</div>`; return; }
 $("#pHist").innerHTML = aviso + `<div class="scroll"><table><thead><tr><th>Fecha</th><th>Datos</th><th class="n">Filas</th><th class="n">Críticas</th><th class="n">Altas</th><th class="n">Medias</th><th>Casos</th><th>Decisión</th><th></th></tr></thead><tbody>` +
  h.map((x,i) => `<tr><td>${esc(x.fecha)}</td><td>${esc(x.origen)}</td><td class="n">${x.n.toLocaleString("es-CO")}</td><td class="n">${x.crit}</td><td class="n">${x.alta}</td><td class="n">${x.media}</td><td>${esc(x.casos)}</td><td class="${x.decision==="Entregar"?"si":"no"}">${x.decision}</td><td style="white-space:nowrap"><button class="btn sec" data-ver="${i}" style="padding:6px 10px;font-size:12px">Ver</button></td></tr>`).join("") + `</tbody></table></div>`;
 document.querySelectorAll("[data-ver]").forEach(b => b.onclick = () => { const x = h[+b.dataset.ver]; mostrar(x.res, x.conCasos); $("#pMsg").className = "msg ok"; $("#pMsg").textContent = `Mostrando la prueba del ${x.fecha} (${x.origen}).`; });
}
$("#hBorrar").onclick = () => { try { localStorage.removeItem(CLAVE_H); } catch(e) {} hMem = []; pintarH([]); };
pintarH();


/* descargas generadas desde la propia página */
function descargar(nombre){ const f = D.archivos[nombre]; if (!f) return;
 let blob;
 if (f.b64) { const bin = atob(f.b64), arr = new Uint8Array(bin.length); for (let i=0;i<bin.length;i++) arr[i] = bin.charCodeAt(i); blob = new Blob([arr], {type:f.tipo}); }
 else blob = new Blob([(f.tipo === "text/csv" ? "\uFEFF" : "") + f.texto], {type: f.tipo + ";charset=utf-8"});
 try { const u = URL.createObjectURL(blob), a = el("a",{href:u, download:nombre}); document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 2000); }
 catch(e) { alertaDescarga(); } }
document.querySelectorAll("[data-dl]").forEach(a => a.onclick = ev => { ev.preventDefault(); descargar(a.dataset.dl); });
function alertaDescarga(){ $("#pMsg").textContent = "Este visor no permite descargas; abre la página publicada en Vercel."; }

/* criterios Gherkin y trazabilidad */
const pintaGk = t => esc(t).replace(/^(\s*)(#.*)$/gm,'$1<span class="c">$2</span>').replace(/^(\s*)(Característica|Escenario|Dado|Cuando|Entonces|Y)\b/gm,'$1<span class="k">$2</span>');
D.features.forEach((f,i) => { const b = el("button",{textContent:({"01":"Ingreso neto","02":"Margen","03":"Total de la compañía","04":"Consistencia metamórfica","05":"Tablero"})[f.archivo.slice(0,2)] || f.archivo, className:i?"":"on"});
 b.onclick = () => { document.querySelectorAll("#tabsGk button").forEach(x=>x.classList.remove("on")); b.classList.add("on"); verGk(f); }; $("#tabsGk").append(b); });
function verGk(f){ $("#gkTexto").innerHTML = pintaGk(f.texto);
 const rs = D.traza.filter(r => r.feature===f.archivo);
 $("#gkReglas").innerHTML = rs.map(r => { const n = D.alertas.filter(a=>a.regla===r.regla).length;
  return `<div class="regla"><b>${r.regla}</b>${esc(r.escenario)}<div style="font-size:12px;color:var(--gris2);margin-top:4px">${n} alertas emitidas por esta regla</div></div>`; }).join("") || `<div class="regla">Sin reglas asociadas.</div>`; }
verGk(D.features[0]);

/* copiar comandos y enlace al repositorio */
document.querySelectorAll(".cmd button").forEach(b => b.onclick = async () => { try { await navigator.clipboard.writeText(b.dataset.c); b.textContent="Copiado"; } catch(e) { b.textContent="Selecciona y copia"; } setTimeout(()=>b.textContent="Copiar",1500); });
$("#repoBox").innerHTML = D.repo ? `<a class="btn" href="${D.repo}" target="_blank" rel="noopener">Ver el repositorio en GitHub</a>` : "";
</script>
</body></html>
"""

if __name__ == "__main__":
    main()
