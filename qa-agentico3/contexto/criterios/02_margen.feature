# language: es
Característica: Margen porcentual (HU-02)

  Escenario: Margen calculado sobre el ingreso
    Dado el ingreso neto mensual y el costo mensual de una tienda
    Cuando se calcula el margen porcentual
    Entonces debe ser (ingreso − costo) / ingreso
    Y no debe calcularse dividiendo por el costo

  Escenario: Margen dentro de rango razonable
    Dado el margen porcentual de cualquier tienda y mes
    Entonces debe estar entre 0 y 0,6
