# language: es
Característica: Ingreso neto (HU-01, HU-04)

  Escenario: Ingreso de cada transacción descuenta el descuento
    Dado una transacción con unidades, precio_lista y descuento
    Cuando se calcula su ingreso
    Entonces el ingreso debe ser unidades × precio_lista × (1 − descuento) con tolerancia de 0,01 COP
    Y el ingreso nunca debe ser negativo ni nulo

  Escenario: Ingreso neto mensual por tienda usa la fecha de factura
    Dado las transacciones de una tienda
    Cuando se calcula el ingreso neto mensual
    Entonces debe ser la suma del ingreso agrupando por el mes de fecha_factura
    Y no debe agruparse por fecha_pedido

  Escenario: Las tiendas pequeñas no venden los domingos
    Dado una tienda de tamaño "pequena"
    Cuando la fecha_factura es domingo
    Entonces las unidades deben ser 0
