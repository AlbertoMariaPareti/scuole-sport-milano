"""Mappa del mondo da un GeoJSON remoto — esercizio introduttivo a GeoPandas.

Il caso piu' semplice: un dataset che GeoPandas legge direttamente da URL,
senza passare da un download manuale. E' il contrasto con l'analisi
principale, dove i geojson del Comune vanno invece scaricati prima di poter
essere aperti.

Uso:
    python esercizi/mappa_mondo.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import matplotlib

URL_CONFINI = (
    "https://raw.githubusercontent.com/datasets/"
    "geo-boundaries-world-110m/master/countries.geojson"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "images" / "mappa_mondo.png",
        help="dove salvare l'immagine",
    )
    parser.add_argument(
        "--mostra", action="store_true", help="apre la finestra interattiva"
    )
    args = parser.parse_args()

    if not args.mostra:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mondo = gpd.read_file(URL_CONFINI)
    print(f"{len(mondo)} geometrie lette, CRS {mondo.crs}")

    fig, ax = plt.subplots(figsize=(12, 6))
    mondo.plot(ax=ax, color="#e8e4dc", edgecolor="#8a8578", linewidth=0.4)
    ax.set_title("Confini nazionali (Natural Earth 110m)")
    ax.set_xlabel("Longitudine")
    ax.set_ylabel("Latitudine")
    ax.set_aspect("equal")
    fig.tight_layout()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=150)
    print(f"Mappa salvata in {args.output}")

    if args.mostra:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
