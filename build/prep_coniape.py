"""Gera CSV dos quantitativos CONIAPE (só PE) e lista de KMLs para o QGIS."""
import csv, json, sys
from pathlib import Path

root = Path(r"C:\Users\tecgeo-jordy\Desktop\CONIAPE")
out = root / "MAPA_PE" / "01_dados"
out.mkdir(parents=True, exist_ok=True)

rows, kml_urb, kml_vias, distritos = [], [], [], []
for d in sorted(root.iterdir()):
    q = d / "quantitativos.json"
    if not (d.is_dir() and q.exists()):
        continue
    j = json.loads(q.read_text(encoding="utf-8"))
    if not str(j["code"]).startswith("26"):
        continue  # PB / RN ficam de fora
    rows.append({
        "CD_MUN": str(j["code"]), "municipio": j["name"], "pasta": d.name,
        "area_urb_km2": round(j["urbanKm2"], 2), "vias_km": round(j["roadsKm"], 2),
        "area_rur_km2": round(j.get("ruralKm2") or 0, 2),
        "setores_urb": j.get("urbanSectors"), "distritos": j.get("parts"),
        "fonte": "CONIAPE (setores IBGE 2022 + vias OSM)",
    })
    for x in j.get("districts", []):
        distritos.append({"CD_MUN": str(j["code"]), "municipio": j["name"],
                          "distrito": x["nome"],
                          # area_km2 é a do distrito inteiro (repete em cada mancha)
                          "area_km2": float(x.get("area_mancha_km2") or x["area_km2"]),
                          "vias_km": float(x["vias_km"])})
    for f, lst in (("01_area_urbana.kml", kml_urb), ("02_vias_urbanas.kml", kml_vias)):
        if (d / f).exists():
            lst.append(str(d / f))

# Ipojuca (pasta CONIAPE\Ipojuca, plano por polígonos) ficou fora do mapa a pedido (15/10/2026)

with open(out / "coniape_pe.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
(out / "distritos.json").write_text(json.dumps(distritos, ensure_ascii=False), encoding="utf-8")
(out / "kml_lists.json").write_text(json.dumps({"urb": kml_urb, "vias": kml_vias}, indent=1), encoding="utf-8")
print(len(rows), "municipios PE;", len(kml_urb), "urb;", len(kml_vias), "vias")
print("area_urb total", round(sum(r["area_urb_km2"] for r in rows), 2),
      "vias total", round(sum(r["vias_km"] for r in rows), 2))
