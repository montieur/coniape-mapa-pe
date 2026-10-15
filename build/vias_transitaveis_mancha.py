"""Vias transitáveis por veículo recortadas nas manchas urbanas do IBGE (PyQGIS standalone).

Para o mapeamento 360°: só conta o trecho de cada via DENTRO das manchas urbanas (setores IBGE 2022
CD_SIT 1-3, como no CONIAPE), e só vias que um carro percorre.

Uso: python-qgis-ltr.bat vias_transitaveis_mancha.py <osm_transitavel.geojson> <pasta> <CD_MUN> <saida.gpkg> <saida.json>
"""
import json, sys
from collections import defaultdict
from pathlib import Path
from qgis.core import (QgsApplication, QgsVectorLayer, QgsFeature, QgsField, QgsFields, QgsGeometry,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject,
                       QgsVectorFileWriter, QgsCoordinateTransformContext, QgsWkbTypes, QgsSpatialIndex)
from qgis.PyQt.QtCore import QVariant

app = QgsApplication([], False); app.initQgis()
src, pasta, cd, out_gpkg, out_json = sys.argv[1:6]
UTM = QgsCoordinateReferenceSystem("EPSG:31985")
base = Path(r"C:\Users\tecgeo-jordy\Desktop\CONIAPE") / pasta

# ---- o que um veículo NÃO percorre (fica de fora e é contabilizado no relatório)
def motivo_exclusao(t):
    if t.get("access") in ("private", "no"): return "acesso privado/proibido"
    if t.get("motor_vehicle") in ("no", "private") or t.get("vehicle") in ("no", "private"): return "proibido a veículos"
    if t.get("service") in ("driveway", "parking_aisle", "drive-through"): return f"service={t['service']}"
    return None

# ---- manchas urbanas (uma por subpasta de Distritos/, com o nome do quantitativos.txt)
def manchas():
    subs = sorted((base / "Distritos").glob("*/area_urbana.kml")) if (base / "Distritos").exists() else []
    for kml, d in ([(s, s.parent) for s in subs] or [(base / "01_area_urbana.kml", None)]):
        lyr = QgsVectorLayer(str(kml), "m", "ogr")
        tr = QgsCoordinateTransform(lyr.crs(), UTM, QgsProject.instance())
        gs = []
        for f in lyr.getFeatures():
            g = QgsGeometry(f.geometry()); g.transform(tr); gs.append(g)
        nome = d.name if d else pasta
        if d and (d / "quantitativos.txt").exists():
            campos = dict(ln.split(":", 1) for ln in (d / "quantitativos.txt").read_text(encoding="utf-8").splitlines() if ":" in ln)
            nome = (campos.get("Mancha") or campos.get("Distrito") or nome).strip()
        yield nome, QgsGeometry.unaryUnion(gs)
M = list(manchas())

osm = QgsVectorLayer(src, "osm", "ogr")
tr = QgsCoordinateTransform(osm.crs(), UTM, QgsProject.instance())
nome_mun = json.loads((base / "quantitativos.json").read_text(encoding="utf-8"))["name"]

fields = QgsFields()
for n, t, l in (("CD_MUN", QVariant.String, 7), ("NM_MUN", QVariant.String, 60), ("NOME_VIA", QVariant.String, 120),
                ("COMP_KM", QVariant.Double, 12), ("TIPO", QVariant.String, 20), ("PAVIMENTO", QVariant.String, 20),
                ("MANCHA", QVariant.String, 60), ("OSM_ID", QVariant.LongLong, 20)):
    fld = QgsField(n, t); fld.setLength(l); fields.append(fld)

out, excl = [], defaultdict(float)
km_mancha, n_mancha, km_tipo = defaultdict(float), defaultdict(int), defaultdict(float)
for f in osm.getFeatures():
    t = {k: f[k] for k in ("highway", "service", "access", "motor_vehicle", "vehicle")}
    g = QgsGeometry(f.geometry()); g.transform(tr)
    mot = motivo_exclusao(t)
    for nome, mg in M:
        if not g.boundingBox().intersects(mg.boundingBox()) or not g.intersects(mg):
            continue
        pedaco = g.intersection(mg)
        if pedaco.isEmpty() or QgsWkbTypes.geometryType(pedaco.wkbType()) != QgsWkbTypes.LineGeometry:
            continue
        km = pedaco.length() / 1000
        if mot:
            excl[mot] += km; continue
        nf = QgsFeature(fields); nf.setGeometry(pedaco)
        nf.setAttributes([cd, nome_mun, f["name"] or f["highway"], round(km, 4), f["highway"],
                          f["surface"], nome, int(f["osm_id"])])
        out.append(nf)
        km_mancha[nome] += km; n_mancha[nome] += 1; km_tipo[f["highway"]] += km

mem = QgsVectorLayer("MultiLineString?crs=EPSG:31985", "vias", "memory")
mem.dataProvider().addAttributes(fields); mem.updateFields()
for nf in out:
    g = nf.geometry(); g.convertToMultiType(); nf.setGeometry(g)
mem.dataProvider().addFeatures(out)
o = QgsVectorFileWriter.SaveVectorOptions(); o.driverName = "GPKG"; o.layerName = "vias_transitaveis"
err = QgsVectorFileWriter.writeAsVectorFormatV3(mem, out_gpkg, QgsCoordinateTransformContext(), o)
assert err[0] == QgsVectorFileWriter.NoError, err

U = QgsGeometry.unaryUnion([g for _, g in M])
total = round(sum(km_mancha.values()), 2)
res = {"criterio": "Vias transitáveis por veículo (OSM), recortadas nas manchas urbanas IBGE 2022 (CD_SIT 1-3)",
       "total": {"vias_km": total, "vias_recortadas_km": total, "n_vias": len(out), "area_urb_km2": round(U.area() / 1e6, 2)},
       "por_tipo_km": {k: round(v, 2) for k, v in sorted(km_tipo.items(), key=lambda x: -x[1])},
       "excluidas_km": {k: round(v, 2) for k, v in excl.items()},
       "manchas": [{"mancha": n, "area_km2": round(g.area() / 1e6, 2), "vias_km": round(km_mancha[n], 2),
                    "vias_recortadas_km": round(km_mancha[n], 2), "n_vias": n_mancha[n]} for n, g in M]}
Path(out_json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: res[k] for k in ("total", "por_tipo_km", "excluidas_km")}, ensure_ascii=False, indent=1))
app.exitQgis()
