"""Aplica em lote o critério 360° (vias transitáveis recortadas nas manchas) nos produtos UTM.

Uso: python-qgis-ltr.bat aplicar_revisao_lote.py <pasta_com_medicoes>
Lê, para cada município, <pasta>_transitavel.gpkg e <pasta>_transitavel.json (saída de vias_transitaveis_mancha.py)
e, como aplicar_revisao_vias.py faz para um município, mas gravando shapefiles e GeoJSON uma vez só:
- troca as vias do município em CONIAPE_PE_UTM25S.gpkg (vias_urbanas)
- atualiza VIAS_KM / DENS_VIAS / FONTE em PE_Municipios_CONIAPE_UTM25S.gpkg
- registra em 01_dados/revisoes.json, preservando o valor original do CONIAPE
"""
import json, sys
from datetime import date
from pathlib import Path
from qgis.core import (QgsApplication, QgsVectorLayer, QgsFeature, QgsVectorFileWriter, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsCoordinateTransformContext)

app = QgsApplication([], False); app.initQgis()
med_dir = Path(sys.argv[1])
CONIAPE = Path(r"C:\Users\tecgeo-jordy\Desktop\CONIAPE")
MP = CONIAPE / "MAPA_PE"
vias = QgsVectorLayer(f"{MP / '02_shape_utm' / 'CONIAPE_PE_UTM25S.gpkg'}|layername=vias_urbanas", "vias", "ogr")
mun = QgsVectorLayer(str(MP / "02_shape_utm" / "PE_Municipios_CONIAPE_UTM25S.gpkg"), "mun", "ogr")
rev_path = MP / "01_dados" / "revisoes.json"
revs = json.loads(rev_path.read_text(encoding="utf-8")) if rev_path.exists() else {}
hoje = date.today()

vias.startEditing(); mun.startEditing()
for js in sorted(med_dir.glob("*_transitavel.json")):
    pasta = js.name[: -len("_transitavel.json")]
    gpkg = med_dir / f"{pasta}_transitavel.gpkg"
    med = json.loads(js.read_text(encoding="utf-8"))
    primeira = next(QgsVectorLayer(str(gpkg), "n", "ogr").getFeatures())   # código e nome vêm das próprias vias
    cd, nome = str(primeira["CD_MUN"]), primeira["NM_MUN"]

    antigas = [f.id() for f in vias.getFeatures(f"\"CD_MUN\" = '{cd}'")]
    vias.deleteFeatures(antigas)
    novas = QgsVectorLayer(str(gpkg), "n", "ogr")
    add = []
    for f in novas.getFeatures():
        nf = QgsFeature(vias.fields()); nf.setGeometry(f.geometry())
        for k in ("CD_MUN", "NM_MUN", "NOME_VIA", "COMP_KM"):
            nf[k] = f[k]
        add.append(nf)
    vias.addFeatures(add)

    km = med["total"]["vias_km"]
    for f in mun.getFeatures(f"\"CD_MUN\" = '{cd}'"):
        orig = revs.get(cd, {}).get("vias_km_original", f["VIAS_KM"])   # valor do CONIAPE, nunca o de uma revisão
        f["VIAS_KM"] = km
        f["DENS_VIAS"] = round(km / f["AREA_URB"], 2) if f["AREA_URB"] else None
        f["FONTE"] = f"CONIAPE + vias OSM transitaveis {hoje:%d/%m/%Y}"
        mun.updateFeature(f)

    anterior = revs.get(cd, {})
    revs[cd] = {"municipio": nome, "data": hoje.isoformat(), "vias_km_original": orig, "vias_km": km,
                "vias_recortadas_km": med["total"]["vias_recortadas_km"],
                # só Caruaru tinha extração incompleta; nos demais a revisão é a padronização do critério
                "motivo": anterior.get("motivo", ""), "criterio": med["criterio"],
                "por_tipo_km": med.get("por_tipo_km"), "excluidas_km": med.get("excluidas_km"),
                "manchas": med["manchas"]}
    print(f"{nome:<28} {orig:>9.2f} -> {km:>9.2f} km  ({len(antigas)} -> {len(add)} trechos)")

assert vias.commitChanges(), vias.commitErrors()
assert mun.commitChanges(), mun.commitErrors()
rev_path.write_text(json.dumps(revs, ensure_ascii=False, indent=1), encoding="utf-8")

ctx = QgsCoordinateTransformContext()
def gravar(layer, dest, crs=None, driver="ESRI Shapefile"):
    o = QgsVectorFileWriter.SaveVectorOptions(); o.driverName = driver; o.fileEncoding = "UTF-8"
    if crs: o.ct = QgsCoordinateTransform(layer.crs(), crs, ctx)
    err = QgsVectorFileWriter.writeAsVectorFormatV3(layer, str(dest), ctx, o)
    assert err[0] == QgsVectorFileWriter.NoError, err
gravar(vias, MP / "02_shape_utm" / "shp" / "CONIAPE_PE_vias_urbanas_UTM25S.shp")
gravar(mun, MP / "02_shape_utm" / "shp" / "PE_Municipios_CONIAPE_UTM25S.shp")
gravar(vias, MP / "01_dados" / "web_vias.geojson", QgsCoordinateReferenceSystem("EPSG:4326"), "GeoJSON")
print("revisões:", len(revs), "| total vias:", round(sum(f["COMP_KM"] for f in vias.getFeatures()), 2), "km")
app.exitQgis()
