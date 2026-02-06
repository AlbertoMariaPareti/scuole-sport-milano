#vogliamo mostrare su una cartina le scuole di Milano
#che hanno in un certo raggio un impianto sportivo 
import geopandas as gpd
import matplotlib.pyplot as plt
import requests #ci serve per fare richieste ad un url
scuole_milano_url = "https://dati.comune.milano.it/dataset/5b4aee8b-8e80-447b-ac91-623544e1c654/resource/a1fa4ea2-31bb-4725-9ca3-89ef0f03a8c8/download/ds78_scuolesecondariesecondogrado_final.geojson"
sport_milano_url = "https://dati.comune.milano.it/dataset/c613f251-6f66-4320-8cac-6ee08d8fd2ef/resource/6811f693-ee63-41ca-9ff7-ea0464f6d600/download/ds34_impianti_sportivi_final.geojson"
#abbiamo visto che questi geojson non consentono di
#creare al volo dei geodataframe,
#quindi scriviamo una funzione per il download
def download_file(url, local_file_name):
    response = requests.get(url) #sisposta grezza (intestazzioni varie + contenuto)
    with open(local_file_name, 'wb') as f:
        f.write(response.content) #scrivo solo il contenuto della risposta

#chiamiamo la funzione per i 2 url 
download_file(scuole_milano_url, 'scuole_milano.geojson')
download_file(sport_milano_url, 'sport_milano.geojson')

#a questo punto creiamo i 2 geodataframe
scuole_gdf = gpd.read_file('scuole_milano.geojson')
sport_gdf = gpd.read_file('sport_milano.geojson')

#dobbiamo impostare il metro come unità di misura delle distanze
scuole_gdf = scuole_gdf.to_crs(epsg=32632)
sport_gdf = sport_gdf.to_crs(epsg=32632)

#creiamo un buffer attorno agli impianti sportivi
raggio = 300

sport_buffer = sport_gdf.buffer(raggio)

#convertiamo il buffer in un geodataframe
sport_buffer_gdf = gpd.GeoDataFrame(geometry=sport_buffer, crs=scuole_gdf.crs)

#facciamo adesso l'intersezione
scuole_near_sport = gpd.overlay(scuole_gdf, sport_buffer_gdf, how='intersection')

#impostiamo i gradi sessagesimali
sport_gdf = sport_gdf.to_crs(epsg=4326)
scuole_near_sport = scuole_near_sport.to_crs(epsg=4326)

#facciamo il grafico
fig, ax = plt.subplots(figsize=(10, 8))
#inserisco tutti gli impianti sportivi
sport_gdf.plot(ax=ax, color='green', label="Impianti Sportivi")
#inseriamo le scuole vicine agli impianti sportivi
scuole_near_sport.plot(ax=ax, color='blue', label='Scuole Vicino Impianti Sportivi', marker='X', markersize=50)
plt.legend()
plt.xlabel("Longitudine")
plt.ylabel("Latitudine")
plt.title(f"Scuole di Milano che hanno un Impianto Sportivo entro un raggio di {raggio} metri")
plt.tight_layout()
plt.show()
