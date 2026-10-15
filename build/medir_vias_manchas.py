"""Mede vias por mancha urbana (PyQGIS standalone, rodar com python-qgis-ltr.bat).

Uso: python-qgis-ltr.bat medir_vias_manchas.py <vias_utm.gpkg> <pasta_municipio> <saida.json>
- inteira: comprimento total das vias que tocam a mancha (critério CONIAPE)
- recortada: só o trecho dentro da mancha
"""
import json, sys
from pathlib import Path
from qgis.core import (QgsApplication, QgsVectorLayer, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsProject, QgsGeometry, QgsSpatialIndex)

app = QgsApplication([], False); app.initQgis()
vias_path, pasta, saida = sys.argv[1:4]
vias = QgsVectorLayer(vias_path, "vias", "ogr")
utm = QgsCoordinateReferenceSystem("EPSG:31985")

feats = {f.id(): f for f in vias.getFeatures()}
idx = QgsSpatialIndex(vias.getFeatures())

def manchas():
    """Uma mancha por subpasta de Distritos/ (com o nome do quantitativos.txt); senão, o KML geral."""
    base = Path(r"C:\Users\tecgeo-jordy\Desktop\CONIAPE") / pasta
    subs = sorted((base / "Distritos").glob("*/area_urbana.kml")) if (base / "Distritos").exists() else []
    alvos = [(s, s.parent) for s in subs] or [(base / "01_area_urbana.kml", None)]
    for kml, d in alvos:
        lyr = QgsVectorLayer(str(kml), "m", "ogr")
        tr = QgsCoordinateTransform(lyr.crs(), utm, QgsProject.instance())
        geoms = []
        for f in lyr.getFeatures():
            g = QgsGeometry(f.geometry()); g.transform(tr); geoms.append(g)
        nome = d.name if d else pasta
        if d and (d / "quantitativos.txt").exists():
            campos = dict(ln.split(":", 1) for ln in (d / "quantitativos.txt").read_text(encoding="utf-8").splitlines() if ":" in ln)
            nome = (campos.get("Mancha") or campos.get("Distrito") or nome).strip()
        yield nome, QgsGeometry.unaryUnion(geoms)

res, todas, uniao = [], set(), []
for nome, g in manchas():
    uniao.append(g)
    ids = [i for i in idx.intersects(g.boundingBox()) if feats[i].geometry().intersects(g)]
    todas.update(ids)
    inteira = sum(feats[i].geometry().length() for i in ids) / 1000
    recortada = sum(feats[i].geometry().intersection(g).length() for i in ids) / 1000
    res.append({"mancha": nome, "area_km2": round(g.area() / 1e6, 2), "vias_km": round(inteira, 2),
                "vias_recortadas_km": round(recortada, 2), "n_vias": len(ids)})

U = QgsGeometry.unaryUnion(uniao)
tot = {"vias_km": round(sum(feats[i].geometry().length() for i in todas) / 1000, 2),
       "vias_recortadas_km": round(sum(feats[i].geometry().intersection(U).length() for i in todas) / 1000, 2),
       "n_vias": len(todas), "area_urb_km2": round(U.area() / 1e6, 2)}
Path(saida).write_text(json.dumps({"total": tot, "manchas": res}, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(tot, ensure_ascii=False))
for r in res: print(r)
app.exitQgis()
