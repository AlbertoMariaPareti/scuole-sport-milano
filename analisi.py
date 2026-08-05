"""Dati e logica dell'analisi, senza nessun output.

Sta separato da `genera_mappa.py` e da `app.py` perche' i due entry point
usano esattamente le stesse funzioni: se la logica vivesse dentro la route
Flask, la versione da riga di comando dovrebbe riscriverla, e le due
finirebbero per rispondere in modo diverso alla stessa domanda.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import folium
import geopandas as gpd
import requests
from folium.plugins import MarkerCluster

# Milano sta nel fuso UTM 32N: proiettando qui le distanze sono in metri veri.
# Farlo *prima* di misurare e' il punto centrale dell'analisi — su EPSG:4326 un
# "raggio di 300" userebbe i gradi come unita', e a questa latitudine un grado
# di longitudine vale circa 78 km contro i 111 km di uno di latitudine.
CRS_METRICO = "EPSG:32632"
CRS_GEOGRAFICO = "EPSG:4326"

CENTRO_MILANO = (45.4642, 9.19)

RADICE = Path(__file__).parent
DATA_DIR = RADICE / "data"

SORGENTI = {
    "scuole": (
        "https://dati.comune.milano.it/dataset/"
        "5b4aee8b-8e80-447b-ac91-623544e1c654/resource/"
        "a1fa4ea2-31bb-4725-9ca3-89ef0f03a8c8/download/"
        "ds78_scuolesecondariesecondogrado_final.geojson"
    ),
    "sport": (
        "https://dati.comune.milano.it/dataset/"
        "c613f251-6f66-4320-8cac-6ee08d8fd2ef/resource/"
        "6811f693-ee63-41ca-9ff7-ea0464f6d600/download/"
        "ds34_impianti_sportivi_final.geojson"
    ),
}


def scarica(nome: str, forza: bool = False) -> Path:
    """Scarica un geojson in data/ una volta sola.

    Il download stava a livello di modulo nella prima versione: con il
    reloader di Flask attivo veniva eseguito due volte a ogni avvio, cioe'
    1,2 MB scaricati per aprire una pagina. Qui parte solo se il file manca.
    """
    DATA_DIR.mkdir(exist_ok=True)
    percorso = DATA_DIR / f"{nome}_milano.geojson"

    if percorso.exists() and not forza:
        return percorso

    print(f"Scarico {nome} ...")
    try:
        risposta = requests.get(SORGENTI[nome], timeout=60)
        risposta.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(
            f"Non riesco a scaricare i dati '{nome}' dal portale del Comune di Milano.\n"
            f"  Causa: {exc.__class__.__name__}\n"
            f"  URL:   {SORGENTI[nome]}\n"
            f"Controlla la connessione, oppure scarica il file a mano e salvalo "
            f"come {percorso}."
        ) from exc

    percorso.write_bytes(risposta.content)
    return percorso


@lru_cache(maxsize=1)
def carica_dati(
    forza_download: bool = False,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """(scuole, impianti) riproiettati in metri, letti da disco una volta sola.

    La cache serve al server: senza, ogni richiesta HTTP rileggerebbe e
    riproietterebbe entrambi i dataset.
    """
    scuole = gpd.read_file(scarica("scuole", forza_download))
    sport = gpd.read_file(scarica("sport", forza_download))
    return scuole.to_crs(CRS_METRICO), sport.to_crs(CRS_METRICO)


def scuole_vicine(
    scuole: gpd.GeoDataFrame, sport: gpd.GeoDataFrame, raggio: int
) -> gpd.GeoDataFrame:
    """Scuole con almeno un impianto entro `raggio` metri, una riga ciascuna.

    La strada intuitiva — buffer attorno agli impianti, poi `sjoin` o
    `overlay` con le scuole — restituisce una riga per ogni coppia
    (scuola, impianto). A 200 metri sono 224 righe per 66 scuole: una scuola
    circondata da tredici impianti verrebbe disegnata tredici volte nello
    stesso punto, e ogni conteggio sarebbe gonfiato di oltre tre volte.

    `sjoin_nearest` con `max_distance` risponde alla domanda giusta —
    "esiste un impianto entro X metri?" — e in piu' restituisce la distanza
    dal piu' vicino, che e' il dato interessante da mostrare nel tooltip.
    """
    vicine = gpd.sjoin_nearest(
        scuole,
        sport[["Nome", "Indirizzo", "geometry"]].rename(
            columns={"Nome": "impianto", "Indirizzo": "impianto_indirizzo"}
        ),
        max_distance=raggio,
        distance_col="distanza_m",
        how="inner",
    )

    # A parita' di distanza minima sjoin_nearest puo' restituire piu' righe
    # per la stessa scuola: teniamo la prima.
    vicine = vicine.sort_values("distanza_m")
    return vicine.loc[~vicine.index.duplicated()].sort_values("distanza_m")


def _testo(valore, fallback: str = "n.d.") -> str:
    """I campi del Comune contengono NaN e stringhe vuote: normalizziamoli."""
    if valore is None:
        return fallback
    testo = str(valore).strip()
    return testo if testo and testo.lower() != "nan" else fallback


def costruisci_mappa(
    vicine: gpd.GeoDataFrame, sport: gpd.GeoDataFrame, raggio: int
) -> folium.Map:
    """Mappa interattiva: impianti raggruppati, scuole in evidenza."""
    vicine_wgs = vicine.to_crs(CRS_GEOGRAFICO)
    sport_wgs = sport.to_crs(CRS_GEOGRAFICO)

    mappa = folium.Map(location=CENTRO_MILANO, zoom_start=12, tiles="CartoDB positron")

    gruppo_sport = folium.FeatureGroup(name=f"Impianti sportivi ({len(sport_wgs)})")
    # 1041 marker singoli rendono la mappa pesante da aprire e illeggibile da
    # zoom lontano: il cluster li accorpa e si aprono avvicinandosi.
    cluster = MarkerCluster().add_to(gruppo_sport)

    for _, riga in sport_wgs.iterrows():
        folium.Marker(
            location=[riga.geometry.y, riga.geometry.x],
            icon=folium.Icon(icon="futbol", prefix="fa", color="green"),
            tooltip=f"{_testo(riga['Nome'], 'Impianto sportivo')} — "
            f"{_testo(riga['Indirizzo'])}",
        ).add_to(cluster)

    gruppo_scuole = folium.FeatureGroup(
        name=f"Scuole con un impianto entro {raggio} m ({len(vicine_wgs)})"
    )

    for _, riga in vicine_wgs.iterrows():
        folium.Marker(
            location=[riga.geometry.y, riga.geometry.x],
            icon=folium.Icon(icon="book", prefix="fa", color="blue"),
            tooltip=(
                f"{_testo(riga['DENOMINAZ'], 'Scuola')} — {_testo(riga['INDIRIZZO'])}"
                f"<br>Impianto piu' vicino: {_testo(riga['impianto'])} "
                f"({riga['distanza_m']:.0f} m)"
            ),
        ).add_to(gruppo_scuole)

    gruppo_sport.add_to(mappa)
    gruppo_scuole.add_to(mappa)
    folium.LayerControl(collapsed=False).add_to(mappa)

    # Folium genera una pagina senza <title>: senza questo, la scheda del
    # browser e le anteprime dei link mostrano l'URL nudo.
    titolo = (
        f"Scuole e impianti sportivi a Milano — {len(vicine_wgs)} scuole "
        f"con un impianto entro {raggio} m"
    )
    mappa.get_root().header.add_child(
        folium.Element(
            f"<title>{titolo}</title>\n"
            f'<meta name="description" content="{titolo}. '
            f'Dati aperti del Comune di Milano.">'
        )
    )

    return mappa


def anteprima_png(
    vicine: gpd.GeoDataFrame,
    sport: gpd.GeoDataFrame,
    totale_scuole: int,
    raggio: int,
    destinazione: Path,
) -> None:
    """Immagine statica per il README: GitHub non renderizza l'HTML della mappa."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 8))
    sport.to_crs(CRS_GEOGRAFICO).plot(
        ax=ax, color="#4c9a6a", markersize=8, alpha=0.55, label="Impianti sportivi"
    )
    vicine.to_crs(CRS_GEOGRAFICO).plot(
        ax=ax,
        color="#1f4e79",
        marker="X",
        markersize=55,
        label=f"Scuole con un impianto entro {raggio} m",
    )

    ax.set_title(
        f"Milano — {len(vicine)} scuole superiori su {totale_scuole} "
        f"hanno un impianto sportivo entro {raggio} m"
    )
    ax.set_xlabel("Longitudine")
    ax.set_ylabel("Latitudine")
    ax.legend(loc="upper right")
    ax.set_aspect("equal")
    fig.tight_layout()

    destinazione.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destinazione, dpi=150)
    plt.close(fig)
