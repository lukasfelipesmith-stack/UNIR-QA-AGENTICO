# language: es
Característica: Ingreso total de la compañía (HU-03)

  Escenario: Solo se suman tiendas activas
    Dado el catálogo de tiendas con sus fechas de actividad
    Cuando se calcula el ingreso total de la compañía para un mes
    Entonces solo deben sumarse las tiendas activas en ese mes
    Y la tienda T10 no debe aparecer desde mayo de 2026

  Escenario: No hay duplicados en la agregación
    Dado las transacciones de un mes
    Cuando se agregan por tienda
    Entonces cada combinación fecha_factura + tienda + producto debe aparecer una sola vez
