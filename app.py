"""Versione server: il raggio diventa un parametro nell'URL.

    python app.py
    http://127.0.0.1:5000/            raggio 300 m
    http://127.0.0.1:5000/?raggio=500

La mappa statica in docs/ risponde a una domanda sola. Qui il server serve
davvero a qualcosa: cambiare il raggio e rivedere il risultato senza
rigenerare niente. La logica e' la stessa di `genera_mappa.py` — entrambi
chiamano `analisi.py`.
"""

from __future__ import annotations

from flask import Flask, request

from analisi import carica_dati, costruisci_mappa, scuole_vicine

app = Flask(__name__)

RAGGIO_MIN, RAGGIO_MAX = 50, 5000


@app.route("/")
def mappa():
    # I dati arrivano dalla cache di carica_dati(): l'elaborazione pesante
    # avviene alla prima richiesta, non a ognuna.
    try:
        raggio = int(request.args.get("raggio", 300))
    except ValueError:
        return "Il parametro 'raggio' deve essere un numero intero di metri.", 400

    if not RAGGIO_MIN <= raggio <= RAGGIO_MAX:
        messaggio = (
            f"Raggio fuori intervallo: usa un valore fra {RAGGIO_MIN} e "
            f"{RAGGIO_MAX} metri."
        )
        return messaggio, 400

    scuole, sport = carica_dati()
    vicine = scuole_vicine(scuole, sport, raggio)

    # get_root().render() restituisce l'HTML direttamente. Salvarlo in
    # templates/ e passarlo a render_template significherebbe far ripassare
    # 1 MB di JavaScript dentro Jinja, che prima o poi incontra una '{{' in un
    # JSON annidato e si rompe — oltre a far scrivere sullo stesso file due
    # richieste contemporanee.
    return costruisci_mappa(vicine, sport, raggio).get_root().render()


if __name__ == "__main__":
    # debug=True attiva il reloader e la pagina di debug interattiva: comodo in
    # sviluppo, da non lasciare acceso su una macchina raggiungibile da fuori.
    app.run(debug=True)
