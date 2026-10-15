"""Tira um município do CONIAPE nos produtos (PyQGIS standalone).

Uso: python-qgis-ltr.bat remover_municipio.py <CD_MUN>
- apaga as vias e as áreas urbanas dele em CONIAPE_PE_UTM25S.gpkg
- na camada de municípios: CONIAPE = 'Nao' e quantitativos do CONIAPE em branco (fica só como referência IBGE)
- regrava os shapefiles e os GeoJSON da web; tira o município de revisoes.json
Depois: prep_coniape.py (se o município vinha de lá), build_data.py e compilar_pacote.py.
"""
import json, sys
from pathlib import Path
from qgis.core import (QgsApplication, QgsVectorLayer, QgsVectorFileWriter, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsCoordinateTransformContext)

app = QgsApplication([], False); app.initQgis()
cd = sys.argv[1]
MP = Path(r"C:\Users\tecgeo-jordy\Desktop\CONIAPE\MAPA_PE")
G = MP / "02_shape_utm" / "CONIAPE_PE_UTM25S.gpkg"
filtro = f"\"CD_MUN\" = '{cd}'"

camadas = {n: QgsVectorLayer(f"{G}|layername={n}", n, "ogr") for n in ("vias_urbanas", "areas_urbanas")}
for n, lyr in camadas.items():
    ids = [f.id() for f in lyr.getFeatures(filtro)]
    lyr.startEditing(); lyr.deleteFeatures(ids)
    assert lyr.commitChanges(), lyr.commitErrors()
    print(f"{n}: {len(ids)} feições removidas")

mun = QgsVectorLayer(str(MP / "02_shape_utm" / "PE_Municipios_CONIAPE_UTM25S.gpkg"), "mun", "ogr")
mun.startEditing()
for f in mun.getFeatures(filtro):
    nome = f["NM_MUN"]
    f["CONIAPE"] = "Nao"
    for k in ("AREA_URB", "AREA_RUR", "VIAS_KM", "PERC_URB", "DENS_VIAS", "SETORES", "DISTRITOS", "FONTE"):
        f[k] = None
    mun.updateFeature(f)
assert mun.commitChanges(), mun.commitErrors()
print("municípios:", nome, "-> fora do CONIAPE")

ctx = QgsCoordinateTransformContext()
def gravar(layer, dest, crs=None, driver="ESRI Shapefile"):
    o = QgsVectorFileWriter.SaveVectorOptions(); o.driverName = driver; o.fileEncoding = "UTF-8"
    if crs: o.ct = QgsCoordinateTransform(layer.crs(), crs, ctx)
    err = QgsVectorFileWriter.writeAsVectorFormatV3(layer, str(dest), ctx, o)
    assert err[0] == QgsVectorFileWriter.NoError, err
shp, wgs = MP / "02_shape_utm" / "shp", QgsCoordinateReferenceSystem("EPSG:4326")
gravar(camadas["vias_urbanas"], shp / "CONIAPE_PE_vias_urbanas_UTM25S.shp")
gravar(camadas["areas_urbanas"], shp / "CONIAPE_PE_areas_urbanas_UTM25S.shp")
gravar(mun, shp / "PE_Municipios_CONIAPE_UTM25S.shp")
gravar(camadas["vias_urbanas"], MP / "01_dados" / "web_vias.geojson", wgs, "GeoJSON")
gravar(camadas["areas_urbanas"], MP / "01_dados" / "web_urb.geojson", wgs, "GeoJSON")

# web_municipios.geojson é a versão simplificada (geometria leve): só os atributos mudam
wm = MP / "01_dados" / "web_municipios.geojson"
d = json.loads(wm.read_text(encoding="utf-8"))
for f in d["features"]:
    if f["properties"]["CD_MUN"] == cd:
        f["properties"].update({"CONIAPE": "Nao", "AREA_URB": None, "AREA_RUR": None, "VIAS_KM": None,
                                "PERC_URB": None, "DENS_VIAS": None, "SETORES": None, "DISTRITOS": None, "FONTE": None})
wm.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")

rp = MP / "01_dados" / "revisoes.json"
revs = json.loads(rp.read_text(encoding="utf-8"))
revs.pop(cd, None)
rp.write_text(json.dumps(revs, ensure_ascii=False, indent=1), encoding="utf-8")
print("revisões restantes:", len(revs))
app.exitQgis()
