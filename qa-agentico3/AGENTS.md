# Proyecto: QA agéntico para cálculos y tableros (TFM UNIR)

## Quién soy y cómo trabajar conmigo
- Somos Nicolás Alfaro Alzate y Jinneth Tique Ortiz, autores del TFM
- Antes de escribir o cambiar código: **muéstrame un plan corto y espera mi "sí"**.
- Ejecuta tú los comandos de terminal (instalar, correr scripts, git). No me pidas que los escriba yo, salvo que sea imprescindible.
- Al terminar cada etapa: corre el código, muéstrame el resultado, y haz `git add . && git commit -m "Etapa X: ..." && git push`.
- Si algo falla, explícame la causa en una frase y corrígelo.

## Objetivo del proyecto
Prototipo de un framework de QA con IA agéntica y ML que valida la consistencia de cálculos (KPIs) y de la capa de visualización (tablero) **antes de la entrega al cliente**, y lo compara con el QA manual.
Empresa ficticia: **Comercial Andina** (10 tiendas, 8 productos, ventas ene–jun 2026, pesos colombianos COP).

## Arquitectura (3 capas)
1. **Contexto**: `contexto/` → metadatos del pipeline (`pipeline.yaml`), historias de usuario, criterios Gherkin (`criterios/*.feature`), reglas de estilo del tablero (`estilo_tablero.yaml`).
2. **Núcleo IA + ML**:
   - Agente evaluador de reglas: lee los Gherkin → genera validaciones (Great Expectations) y relaciones metamórficas → las ejecuta.
   - Detector de anomalías estadísticas: PyOD (`src/detectores.py`).
   - Agente auditor del tablero: compara `datos/tablero.json` contra los KPIs y contra `estilo_tablero.yaml`.
3. **Gobernanza**: alertas con severidad y explicación en lenguaje de negocio → compuerta de aprobación humana (HITL) por consola → registro de decisiones.

## Estructura de carpetas
- `src/` código Python
- `contexto/` insumos de negocio, incluida la línea base real de Jira (`linea_base_jira.yaml`) (NO modificar sin preguntarme)
- `datos/` datos sintéticos generados
- `resultados/` métricas, alertas, gráficas
- `web/` página interactiva de resultados (se publica en Vercel con `web` como raíz); `src/generar_pagina.py` la regenera. Para mostrar el botón del repositorio, poner su URL en `REPO_URL`

## Reglas técnicas
- Python 3.11+, entorno virtual en `.venv`. Dependencias en `requirements.txt`.
- **Regla de oro del experimento:** los detectores y agentes NUNCA leen `datos/anomalias_verdad.csv` ni la columna `etiqueta`. Eso es solo para calificar al final. Si la leen, el experimento queda invalidado.
- Semillas aleatorias fijas → resultados reproducibles.
- Los LLM se llaman lo menos posible: el agente genera las reglas una vez y se guardan en `resultados/reglas_generadas/`; la evaluación masiva es determinista.
- Claude Agent SDK: autenticar con la sesión de Claude Code (no usar ANTHROPIC_API_KEY).
- Código simple y comentado en español.

## Estado actual (prototipo v1, 9-nov-2026)
Ya construido y funcionando:
- `src/generador_datos.py` + `src/inyector_anomalias.py` + `src/generar_escenario.py`: escenario sintético con 273 anomalías en 5 familias (datos, contextual, cálculo, semántica, visualización).
- `src/metodos_clasicos.py`: líneas base (reglas genéricas Pandera, ML PyOD).
- `src/framework_agentico.py`: agente evaluador (reglas R01–R11 trazadas a cada escenario Gherkin, generadas por LLM en modo asistido), agente auditor del tablero (T01–T03), alertas con severidad y explicación.
- `src/revision_humana.py`: compuerta HITL por consola.
- `src/evaluar.py`: compara 4 métodos y genera tabla, gráficas y reporte.
- `src/generar_datos_prueba.py`: paquete de prueba descargable (web/pruebas/, 14 casos documentados). Es independiente: NO modifica datos/ ni resultados/.
- La página (web/index.html) incluye 'Prueba el modelo': ejecuta en el navegador las reglas R01, R02, R04, R08, R03, R05, R06 y una detección estadística ligera sobre CSV que cargue el usuario.

Siguiente iteración (v2), en este orden:
1. Automatizar el agente evaluador con Claude Agent SDK + gx-mcp-server: que lea los .feature y genere las reglas solo (hoy están en REGLAS_EVALUADOR, escritas con ayuda de un LLM).
2. Explicaciones de alertas redactadas por el LLM en lote (hoy son plantillas).
3. Comparar Claude vs Gemini como evaluadores.
4. Reemplazar los supuestos MANUAL y HITL_MIN de `src/evaluar.py` por datos reales (Jira y decisiones_hitl.csv).

## Comandos
- Crear el escenario de prueba: `python src/generar_escenario.py`
- Ejecutar y calificar los 4 métodos: `python src/evaluar.py`
- Revisión humana: `python src/revision_humana.py`
- Paquete de prueba: `python src/generar_datos_prueba.py`
