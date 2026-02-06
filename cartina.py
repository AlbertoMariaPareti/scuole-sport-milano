#vogliamo realizzare una cartina del mondo,
#utilizzando la libreria geopandas e un file geojson
#scaricabile da Internet contenente dati spaziali delle 
#principali città del mondo
import geopandas as gpd
import matplotlib.pyplot as plt

#vediamo se è possibile creare al volo un geodataframe
url = "https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/master/countries.geojson"
gdf = gpd.read_file(url)
print(gdf)

#facciamo il grafico
fig, ax = plt.subplots(figsize=(10, 6))
#applico il grafico al gdf
gdf.plot(ax=ax, color='red', edgecolor='blue')
plt.title("Cartina Mondiale")
plt.xlabel("Longitudine")
plt.ylabel("Latitudine")
plt.show()

