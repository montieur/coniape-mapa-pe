"""GeoJSON OSM (WGS84) -> GPKG UTM 25S só com as vias que tocam 01_area_urbana.kml.
Uso: python-qgis-ltr.bat osm_para_utm.py <geojson> <pasta_municipio> <saida.gpkg>"""
import sys
from pathlib import Path
from qgis.core import (QgsApplication, QgsVectorLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsProject, QgsGeometry, QgsVectorFileWriter, QgsFeature, QgsWkbTypes, QgsSpatialIndex)
app = QgsApplication([], False); app.initQgis()
src, pasta, out = sys.argv[1:4]
utm = QgsCoordinateReferenceSystem("EPSG:31985")
base = Path(r"C:\Users\tecgeo-jordy\Desktop\CONIAPE") / pasta
vias = QgsVectorLayer(src, "v", "ogr")
tr = QgsCoordinateTransform(vias.crs(), utm, QgsProject.instance())
urb = QgsVectorLayer(str(base / "01_area_urbana.kml"), "u", "ogr")
tru = QgsCoordinateTransform(urb.crs(), utm, QgsProject.instance())
gs = []
for f in urb.getFeatures():
    g = QgsGeometry(f.geometry()); g.transform(tru); gs.append(g)
U = QgsGeometry.unaryUnion(gs)
eng = QgsGeometry.createGeometryEngine(U.constGet()); eng.prepareGeometry()
opts = QgsVectorFileWriter.SaveVectorOptions(); opts.driverName = "GPKG"
w = QgsVectorFileWriter.create(out, vias.fields(), QgsWkbTypes.LineString, utm, QgsProject.instance().transformContext(), opts)
n = tot = 0
for f in vias.getFeatures():
    g = QgsGeometry(f.geometry()); g.transform(tr); tot += 1
    if eng.intersects(g.constGet()):
        nf = QgsFeature(f); nf.setGeometry(g); w.addFeature(nf); n += 1
del w
print(f"{n}/{tot} vias tocam a mancha -> {out}")
app.exitQgis()
