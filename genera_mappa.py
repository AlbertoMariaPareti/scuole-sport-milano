"""Genera la mappa interattiva come file HTML autonomo.

E' l'entry point principale: produce `docs/index.html`, che GitHub Pages
pubblica cosi' com'e'. Chi apre il repo vede la mappa con un click, senza
clonare niente e senza avviare un server.

Uso:
    python genera_mappa.py                  # raggio 300 m
    python genera_mappa.py --raggio 500
    python genera_mappa.py --csv scuole.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

from analisi import RADICE, anteprima_png, carica_dati, costruisci_mappa, scuole_vicine


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--raggio", type=int, default=300, help="raggio in metri (default: 300)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=RADICE / "docs" / "index.html",
        help="dove salvare la mappa interattiva",
    )
    parser.add_argument(
        "--anteprima",
        type=Path,
        default=None,
        help="PNG statico per il README (default: images/anteprima_<raggio>m.png)",
    )
    parser.add_argument(
        "--csv", type=Path, default=None, help="esporta l'elenco delle scuole trovate"
    )
    parser.add_argument(
        "--aggiorna-dati",
        action="store_true",
        help="riscarica i geojson anche se gia' presenti",
    )
    args = parser.parse_args()

    scuole, sport = carica_dati(args.aggiorna_dati)
    vicine = scuole_vicine(scuole, sport, args.raggio)

    print(
        f"{len(vicine)} scuole su {len(scuole)} "
        f"({len(vicine) / len(scuole):.0%}) hanno un impianto sportivo "
        f"entro {args.raggio} m."
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    costruisci_mappa(vicine, sport, args.raggio).save(str(args.output))
    print(f"Mappa interattiva salvata in {args.output}")

    anteprima = args.anteprima or (RADICE / "images" / f"anteprima_{args.raggio}m.png")
    anteprima_png(vicine, sport, len(scuole), args.raggio, anteprima)
    print(f"Anteprima salvata in {anteprima}")

    if args.csv:
        colonne = [
            "DENOMINAZ",
            "INDIRIZZO",
            "NIL",
            "impianto",
            "impianto_indirizzo",
            "distanza_m",
        ]
        esistenti = [c for c in colonne if c in vicine.columns]
        vicine[esistenti].round({"distanza_m": 1}).to_csv(args.csv, index=False)
        print(f"Elenco salvato in {args.csv}")


if __name__ == "__main__":
    main()
