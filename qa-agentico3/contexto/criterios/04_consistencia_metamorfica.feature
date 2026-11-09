# language: es
Característica: Relaciones metamórficas de los KPIs

  Escenario: La suma de las partes es igual al total
    Dado los ingresos netos mensuales por tienda
    Cuando se suman todas las tiendas activas de un mes
    Entonces el resultado debe ser igual al ingreso total de la compañía de ese mes

  Escenario: Reordenar los datos no cambia los KPIs
    Dado el conjunto de transacciones
    Cuando se reordenan aleatoriamente las filas y se recalculan los KPIs
    Entonces todos los KPIs deben ser idénticos

  Escenario: Duplicar precios duplica el ingreso pero no las unidades
    Dado el conjunto de transacciones
    Cuando se multiplican todos los precios_lista por 2 y se recalculan los KPIs
    Entonces el ingreso neto mensual debe duplicarse
    Y las unidades mensuales no deben cambiar
