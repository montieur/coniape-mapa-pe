"""Baixa do OpenStreetMap (Overpass) as vias de um município com o mesmo filtro do CONIAPE.

Uso:  python -I osm_vias_municipio.py <pasta_do_municipio>   (ex.: 08_Caruaru)
Saída: MAPA_PE/00_osm_download/<pasta>_osm_vias.geojson  (todas as vias do retângulo do município;
       a seleção das que tocam as manchas urbanas é feita depois, no QGIS)
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

CONIAPE = Path(r"C:\Users\tecgeo-jordy\Desktop\CONIAPE")
# tipos de highway presentes nos KMLs de vias do CONIAPE
TIPOS = "trunk|primary|secondary|tertiary|unclassified|residential|living_street|service"
ENDPOINTS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
             "https://overpass.private.coffee/api/interpreter")

pasta = sys.argv[1]
lim = (CONIAPE / pasta / "03_limite_municipal.kml").read_text(encoding="utf-8")
pts = [tuple(map(float, p.split(",")[:2])) for c in re.findall(r"<coordinates>(.*?)</coordinates>", lim, re.S) for p in c.split()]
W, E = min(p[0] for p in pts) - .005, max(p[0] for p in pts) + .005
S, N = min(p[1] for p in pts) - .005, max(p[1] for p in pts) + .005

q = f'[out:json][timeout:240];way["highway"~"^({TIPOS})$"]({S},{W},{N},{E});out tags geom;'
data = None
for tentativa in range(3):
    for ep in ENDPOINTS:
        try:
            req = urllib.request.Request(ep, data=urllib.parse.urlencode({"data": q}).encode(),
                                         headers={"User-Agent": "TECGEO-CONIAPE/1.0"})
            data = json.load(urllib.request.urlopen(req, timeout=300))
            print("endpoint:", ep); break
        except Exception as e:
            print("falhou", ep, e)
    if data: break
    time.sleep(20)
if not data:
    sys.exit("Overpass indisponível")

feats = [{"type": "Feature",
          "properties": {"osm_id": e["id"], "highway": e["tags"].get("highway"), "name": e["tags"].get("name")},
          "geometry": {"type": "LineString", "coordinates": [[g["lon"], g["lat"]] for g in e["geometry"]]}}
         for e in data["elements"] if e.get("geometry")]
out = CONIAPE / "MAPA_PE" / "00_osm_download"
out.mkdir(exist_ok=True)
dest = out / f"{pasta}_osm_vias.geojson"
dest.write_text(json.dumps({"type": "FeatureCollection", "features": feats,
                            "osm_base": data.get("osm3s", {}).get("timestamp_osm_base")}), encoding="utf-8")
print(len(feats), "vias ->", dest, "| base OSM:", data.get("osm3s", {}).get("timestamp_osm_base"))
