"""Substitui as vias de um município nos produtos UTM pelas re-extraídas do OSM (PyQGIS standalone).

Uso: python-qgis-ltr.bat aplicar_revisao_vias.py <CD_MUN> <vias_novas_utm.gpkg> <medicao.json>
- troca as feições do município em CONIAPE_PE_UTM25S.gpkg (vias_urbanas)
- atualiza VIAS_KM / DENS_VIAS / FONTE em PE_Municipios_CONIAPE_UTM25S.gpkg
- regrava os shapefiles e o web_vias.geojson
- registra a revisão em 01_dados/revisoes.json (lido por build_data.py)
"""
import json, sys
from datetime import date
from pathlib import Path
from qgis.core import (QgsApplication, QgsVectorLayer, QgsFeature, QgsVectorFileWriter,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransformContext)

app = QgsApplication([], False); app.initQgis()
cd, novas_path, medicao_path = sys.argv[1:4]
MP = Path(r"C:\Users\tecgeo-jordy\Desktop\CONIAPE\MAPA_PE")
GPKG_VIAS = MP / "02_shape_utm" / "CONIAPE_PE_UTM25S.gpkg"
GPKG_MUN = MP / "02_shape_utm" / "PE_Municipios_CONIAPE_UTM25S.gpkg"
med = json.loads(Path(medicao_path).read_text(encoding="utf-8"))

# 1) vias: remove as antigas do município e grava as novas
vias = QgsVectorLayer(f"{GPKG_VIAS}|layername=vias_urbanas", "vias", "ogr")
antes = sum(f["COMP_KM"] for f in vias.getFeatures(f"\"CD_MUN\" = '{cd}'"))
novas = QgsVectorLayer(novas_path, "novas", "ogr")
vias.startEditing()
vias.deleteFeatures([f.id() for f in vias.getFeatures(f"\"CD_MUN\" = '{cd}'")])
add = []
for f in novas.getFeatures():
    nf = QgsFeature(vias.fields()); nf.setGeometry(f.geometry())
    for k in ("CD_MUN", "NM_MUN", "NOME_VIA", "COMP_KM"):
        nf[k] = f[k]
    add.append(nf)
vias.addFeatures(add)
assert vias.commitChanges(), vias.commitErrors()
depois = sum(f["COMP_KM"] for f in vias.getFeatures(f"\"CD_MUN\" = '{cd}'"))
print(f"vias {cd}: {antes:.2f} km -> {depois:.2f} km ({len(add)} trechos)")

# 2) município: novos quantitativos
mun = QgsVectorLayer(str(GPKG_MUN), "mun", "ogr")
mun.startEditing()
nome = None
for f in mun.getFeatures(f"\"CD_MUN\" = '{cd}'"):
    nome = f["NM_MUN"]; orig = f["VIAS_KM"]
    f["VIAS_KM"] = med["total"]["vias_km"]
    f["DENS_VIAS"] = round(med["total"]["vias_km"] / f["AREA_URB"], 2)
    f["FONTE"] = f"CONIAPE + vias OSM revisadas em {date.today():%d/%m/%Y}"
    mun.updateFeature(f)
assert mun.commitChanges(), mun.commitErrors()

# 3) shapefiles e GeoJSON web
ctx = QgsCoordinateTransformContext()
def gravar(layer, dest, crs=None, driver="ESRI Shapefile"):
    o = QgsVectorFileWriter.SaveVectorOptions(); o.driverName = driver; o.fileEncoding = "UTF-8"
    if crs: o.ct = __import__("qgis.core", fromlist=["QgsCoordinateTransform"]).QgsCoordinateTransform(layer.crs(), crs, ctx)
    err = QgsVectorFileWriter.writeAsVectorFormatV3(layer, str(dest), ctx, o)
    assert err[0] == QgsVectorFileWriter.NoError, err
shp = MP / "02_shape_utm" / "shp"
gravar(vias, shp / "CONIAPE_PE_vias_urbanas_UTM25S.shp")
gravar(mun, shp / "PE_Municipios_CONIAPE_UTM25S.shp")
gravar(vias, MP / "01_dados" / "web_vias.geojson", QgsCoordinateReferenceSystem("EPSG:4326"), "GeoJSON")

# 4) registro da revisão
rev_path = MP / "01_dados" / "revisoes.json"
revs = json.loads(rev_path.read_text(encoding="utf-8")) if rev_path.exists() else {}
orig = revs.get(cd, {}).get("vias_km_original", orig)   # sempre o valor do CONIAPE, não o de uma revisão anterior
revs[cd] = {"municipio": nome, "data": date.today().isoformat(), "vias_km_original": orig,
            "vias_km": med["total"]["vias_km"], "vias_recortadas_km": med["total"]["vias_recortadas_km"],
            # aviso só quando houve falha na extração original (Caruaru); senão é a padronização do critério
            "motivo": revs.get(cd, {}).get("motivo", ""),
            "criterio": med.get("criterio", "Vias reextraídas do OpenStreetMap com o mesmo filtro e critério do CONIAPE "
                                            "(vias que tocam as manchas urbanas, comprimento inteiro)."),
            "por_tipo_km": med.get("por_tipo_km"), "excluidas_km": med.get("excluidas_km"),
            "manchas": med["manchas"]}
rev_path.write_text(json.dumps(revs, ensure_ascii=False, indent=1), encoding="utf-8")
print("revisão registrada:", rev_path)
app.exitQgis()
