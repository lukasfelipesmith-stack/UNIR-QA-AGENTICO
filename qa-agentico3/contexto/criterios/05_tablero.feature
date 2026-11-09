# language: es
Característica: Capa de visualización del tablero (HU-05)

  Escenario: Los valores del tablero coinciden con los KPIs calculados
    Dado el tablero exportado y los KPIs del pipeline
    Cuando se compara cada valor mostrado con su KPI
    Entonces la diferencia debe ser menor a 500 COP para el ingreso
    Y menor a 0,05 puntos porcentuales para el margen

  Escenario: Formato de moneda y porcentaje
    Dado un valor monetario del tablero
    Entonces debe mostrarse en COP con el formato "$ 1.234.567"
    Y el margen debe mostrarse en escala 0–100 con un decimal y símbolo "%"

  Escenario: Títulos y periodo correctos
    Dado cada visual del tablero
    Entonces su título debe coincidir con el definido en estilo_tablero.yaml
    Y el mes mostrado debe coincidir con el mes del filtro seleccionado
