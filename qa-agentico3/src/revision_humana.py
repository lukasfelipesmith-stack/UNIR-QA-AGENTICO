"""
Compuerta de aprobación humana (Human-in-the-Loop).

Muestra en la terminal las alertas críticas y una muestra de las alertas de ML (severidad media),
una por una. El experto responde:
   a = aprobar (es un error real)   r = rechazar (falso positivo)   c = comentario   s = salir
Las decisiones y el tiempo de cada una se guardan en resultados/decisiones_hitl.csv.

Uso:  python src/revision_humana.py
"""
import csv
import json
import random
import time
from datetime import datetime
from pathlib import Path

RES = Path(__file__).resolve().parent.parent / "resultados"


def main():
    alertas = json.loads((RES / "alertas.json").read_text(encoding="utf-8"))
    criticas = [a for a in alertas if a["severidad"] == "crítica"]
    medias = [a for a in alertas if a["severidad"] == "media"]
    random.Random(1).shuffle(medias)
    cola = criticas + medias[:10]
    archivo = RES / "decisiones_hitl.csv"
    nuevo = not archivo.exists()
    print(f"\nRevisión humana: {len(criticas)} alertas críticas + 10 de ML (muestra). Escribe s para salir.\n")
    with open(archivo, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha_hora", "alerta", "severidad", "regla", "decision", "comentario", "segundos"])
        for n, a in enumerate(cola, 1):
            print(f"[{n}/{len(cola)}] {a['id']} · {a['severidad'].upper()} · {a['regla']} · {a['criterio_origen']}")
            print(f"   {a['explicacion']}")
            t0 = time.time()
            r = ""
            while r not in ("a", "r", "c", "s"):
                r = input("   ¿Decisión? (a=aprobar, r=rechazar, c=comentario, s=salir): ").strip().lower()
            if r == "s":
                break
            comentario = input("   Comentario: ").strip() if r == "c" else ""
            w.writerow([datetime.now().isoformat(timespec="seconds"), a["id"], a["severidad"], a["regla"],
                        {"a": "aprobada", "r": "rechazada", "c": "comentada"}[r], comentario, round(time.time() - t0, 1)])
            print()
    print(f"Decisiones guardadas en {archivo}")


if __name__ == "__main__":
    main()
