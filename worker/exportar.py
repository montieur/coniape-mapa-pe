"""GIS Comercial · arquivos GIS de um município: Shapefile (.zip), KML e KMZ.

Camadas (todas as que tiverem feições):
  limite_municipal  limite do município (união dos setores censitários IBGE 2022)
  area_urbana       manchas urbanas (setores CD_SIT 1, 2 ou 3)
  area_rural        o restante do município (limite menos a área urbana)
  vias_urbanas      vias transitáveis por veículo (OSM) dentro das manchas urbanas
  vias_rurais       vias transitáveis por veículo (OSM) fora das manchas urbanas

Shapefile: SIRGAS 2000 / UTM do fuso do município (os mesmos produtos do mapa). KML/KMZ: WGS 84, como o Google Earth espera.
"""
import re
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

import geopandas as gpd
from shapely.geometry import MultiLineString, MultiPolygon

# chave, título, estilo KML (cores aabbggrr), largura, preenchimento
CAMADAS = [
    ("limite_municipal", "Limite do município", "ff8c6e0f", 3.0, None),
    ("area_urbana", "Área urbana (manchas IBGE 2022)", "ff2c76e8", 1.5, "592c76e8"),
    ("area_rural", "Área rural", "ff4a9a5a", 1.0, "334a9a5a"),
    ("vias_urbanas", "Vias urbanas transitáveis (OSM)", "ff2b39c0", 1.4, None),
    ("vias_rurais", "Vias rurais transitáveis (OSM)", "ff2b5a8a", 1.2, None),
]


def nome_base(uf, nome):
    s = unicodedata.normalize("NFD", nome).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")
    return f"GIS-Comercial_{uf}_{s}"


def _coords(seq):
    return " ".join(f"{x:.6f},{y:.6f},0" for x, y, *_ in seq)


def _poligono(p):
    xml = f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{_coords(p.exterior.coords)}</coordinates></LinearRing></outerBoundaryIs>"
    for r in p.interiors:
        xml += f"<innerBoundaryIs><LinearRing><coordinates>{_coords(r.coords)}</coordinates></LinearRing></innerBoundaryIs>"
    return xml + "</Polygon>"


def _geom_kml(g):
    t = g.geom_type
    if t == "Polygon":
        return _poligono(g)
    if t == "LineString":
        return f"<LineString><coordinates>{_coords(g.coords)}</coordinates></LineString>"
    return "<MultiGeometry>" + "".join(_geom_kml(p) for p in g.geoms) + "</MultiGeometry>"


def _dados(linha, colunas):
    return "<ExtendedData>" + "".join(
        f'<Data name="{c}"><value>{escape(str(linha[c]))}</value></Data>' for c in colunas
        if linha[c] is not None and str(linha[c]) != "nan") + "</ExtendedData>"


def _nome_placemark(chave, linha, titulo_mun):
    if chave == "limite_municipal":
        return titulo_mun
    if chave == "area_urbana":
        return linha.get("MANCHA") or "Mancha urbana"
    if chave == "area_rural":
        return "Área rural"
    return (linha.get("NOME") or linha.get("TIPO") or "Via") or "Via"


def kml(titulo, camadas_wgs, descricao):
    estilos, pastas = [], []
    for chave, tit, cor, larg, fundo in CAMADAS:
        gdf = camadas_wgs.get(chave)
        if gdf is None or gdf.empty:
            continue
        preench = f"<PolyStyle><color>{fundo}</color><fill>1</fill><outline>1</outline></PolyStyle>" if fundo else "<PolyStyle><fill>0</fill></PolyStyle>"
        estilos.append(f'<Style id="{chave}"><LineStyle><color>{cor}</color><width>{larg}</width></LineStyle>{preench}</Style>')
        colunas = [c for c in gdf.columns if c != "geometry"]
        marcas = []
        for _, ln in gdf.iterrows():
            marcas.append(f"<Placemark><name>{escape(str(_nome_placemark(chave, ln, titulo)))}</name><styleUrl>#{chave}</styleUrl>"
                          f"{_dados(ln, colunas)}{_geom_kml(ln.geometry)}</Placemark>")
        pastas.append(f"<Folder><name>{escape(tit)} ({len(gdf)})</name>{''.join(marcas)}</Folder>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f"<name>{escape(titulo)}</name><description>{escape(descricao)}</description>"
            + "".join(estilos) + "".join(pastas) + "</Document></kml>\n")


def leia_me(meta, epsg, camadas, fontes):
    linhas = [
        f"GIS Comercial · {meta['nome']} - {meta['uf']} (código IBGE {meta['cd']})",
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "", "CAMADAS",
    ]
    for chave, tit, *_ in CAMADAS:
        g = camadas.get(chave)
        if g is not None and not g.empty:
            linhas.append(f"  {chave}.shp - {tit}: {len(g)} feição(ões)")
    linhas += [
        "", "SISTEMA DE COORDENADAS",
        f"  Shapefile: SIRGAS 2000 / UTM, fuso do município (EPSG:{epsg}). KML/KMZ: WGS 84 (EPSG:4326).",
        "", "FONTES",
        "  Limite e áreas: IBGE, malha de setores censitários do Censo 2022 (área urbana = situação 1, 2 ou 3; rural = o restante).",
        "  Vias: OpenStreetMap, só as transitáveis por veículo (trunk, primary, secondary, tertiary, unclassified, residential,",
        "        living_street, service, road, track e as alças *_link), sem vias privadas nem corredores de estacionamento e garagem.",
        f"  Base do OpenStreetMap: {fontes.get('osm', {}).get('base') or fontes.get('osm_rural', {}).get('base') or 'ver arquivo do município'}.",
        "", "LICENÇA E ATRIBUIÇÃO",
        "  Contém dados do OpenStreetMap © colaboradores do OpenStreetMap, disponíveis sob a licença ODbL",
        "  (https://www.openstreetmap.org/copyright). Ao usar ou redistribuir as vias, mantenha essa atribuição.",
        "  Dados do IBGE: uso livre com citação da fonte.",
    ]
    return "\n".join(linhas) + "\n"


def exportar(meta, epsg, camadas_utm, fontes, pasta):
    """Escreve <base>_shp.zip, <base>.kml e <base>.kmz em `pasta`. Retorna {'shp','kml','kmz','camadas'}."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    base = nome_base(meta["uf"], meta["nome"])
    camadas = {k: g for k, g in camadas_utm.items() if g is not None and not g.empty}

    # Shapefile (UTM), uma camada por arquivo, tudo num zip com o LEIA-ME
    tmp = pasta / f"_{base}_shp"
    tmp.mkdir(exist_ok=True)
    for chave, gdf in camadas.items():
        gdf.to_file(tmp / f"{chave}.shp", driver="ESRI Shapefile", encoding="utf-8")
    texto = leia_me(meta, epsg, camadas, fontes)
    (tmp / "LEIA-ME.txt").write_text(texto, encoding="utf-8")
    shp = pasta / f"{base}_shp.zip"
    with zipfile.ZipFile(shp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(tmp.iterdir()):
            z.write(f, f"{base}/{f.name}")
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()

    # KML / KMZ (WGS 84)
    wgs = {k: g.to_crs(4326) for k, g in camadas.items()}
    titulo = f"{meta['nome']} - {meta['uf']}"
    doc = kml(titulo, wgs, "GIS Comercial: limite, áreas urbana e rural e vias transitáveis. Fontes: IBGE (setores 2022) e OpenStreetMap (© colaboradores, ODbL).")
    arq_kml = pasta / f"{base}.kml"
    arq_kml.write_text(doc, encoding="utf-8")
    arq_kmz = pasta / f"{base}.kmz"
    with zipfile.ZipFile(arq_kmz, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", doc)

    resumo = {}
    for chave, gdf in camadas.items():
        r = {"n": int(len(gdf))}
        if "COMP_KM" in gdf:
            r["km"] = round(float(gdf["COMP_KM"].sum()), 2)
        if "AREA_KM2" in gdf:
            r["km2"] = round(float(gdf["AREA_KM2"].sum()), 2)
        resumo[chave] = r
    return {"shp": shp, "kml": arq_kml, "kmz": arq_kmz, "camadas": resumo}
