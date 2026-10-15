"""Do GeoJSON 'transitavel', extrai só os tipos do filtro CONIAPE (mesma consulta, mesmo retângulo)."""
import json, sys
TIPOS = set("trunk|primary|secondary|tertiary|unclassified|residential|living_street|service".split("|"))
d = json.load(open(sys.argv[1], encoding="utf-8"))
d["features"] = [f for f in d["features"] if f["properties"].get("highway") in TIPOS]
json.dump(d, open(sys.argv[2], "w", encoding="utf-8"))
print(len(d["features"]), "vias filtro CONIAPE")
