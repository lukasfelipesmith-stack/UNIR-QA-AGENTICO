# QA agéntico para cálculos y tableros — Comercial Andina

**Trabajo Fin de Máster · Máster en Transformación Digital · UNIR**
Autores: Nicolás Alfaro y Jinneth Tique Ortiz

Prototipo (v1, segunda entrega) de un framework de QA con IA agéntica y machine learning que valida la consistencia de los cálculos (KPIs) y de la capa de visualización (tablero) **antes de la entrega al cliente**, y lo compara con el QA manual.

## Resultados principales
- El framework detecta **267 de 273** errores inyectados (98 %), con F1 de 0,88.
- Detecta el **100 %** de los errores semánticos y de visualización; las reglas genéricas y el machine learning, el 0 %.
- Línea base real (Jira): el QA operativo consume el **53,7 %** de las horas del proyecto.
- Tiempo de ciclo de QA estimado: de 11,0 h a 3,2 h (−71 %), con supuestos conservadores.

## Ejecutar
Requiere Python 3.11 o superior.
```
pip install -r requirements.txt
python src/generar_escenario.py
python src/evaluar.py
python src/revision_humana.py
```
Paquete de prueba descargable (14 errores documentados, independiente del experimento): `python src/generar_datos_prueba.py` → `web/pruebas/`.

La página de resultados queda en `web/index.html`. Permite descargar los resultados del experimento (`web/descargas/`), probar el revisor con el paquete de prueba o con CSV propios, y guarda el historial de pruebas en el navegador. Se genera con `python src/generar_pagina.py`; la página se abre en cualquier navegador y se publica en Vercel con la carpeta `web` como raíz.

## Estructura
| Carpeta | Contenido |
| --- | --- |
| `contexto/` | Intención del negocio: criterios Gherkin, historias de usuario, definición de KPIs, reglas de estilo del tablero y línea base real de Jira |
| `src/` | Código: generación de datos, inyección de anomalías, métodos clásicos, framework, revisión humana, evaluación y página |
| `datos/` | Escenario sintético generado (Comercial Andina) |
| `resultados/` | Métricas, alertas, trazabilidad, reporte de entrega y gráficas |
| `docs/` | Texto de avance del TFM |
| `web/` | Página interactiva de resultados (incluye Chart.js, licencia MIT, en `web/vendor/`) |

## Alcance de la v1
Las reglas del agente evaluador se generaron con un modelo de lenguaje en modo asistido y corren como código determinista. Los agentes con LLM en ejecución, MCP/RAG y el auditor multimodal corresponden a la siguiente entrega. Los datos son 100 % sintéticos; no contienen información personal ni de clientes.

Desarrollado con apoyo de asistentes de inteligencia artificial, con dirección y validación de los autores.
