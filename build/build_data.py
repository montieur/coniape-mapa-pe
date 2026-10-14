"""Monta data.js (dados compactos do mapa) e copia os relatórios PDF de PE.

Uso:  python -I build_data.py
Entradas: ../../01_dados/web_*.geojson, distritos.json  (exportados do QGIS)
Saídas:   ../data.js  e  ../relatorios/*.pdf
"""
import json, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
DADOS = SITE.parent / "01_dados"
CONIAPE = SITE.parent.parent


def rnd(coords, nd):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], nd), round(coords[1], nd)]
    return [rnd(c, nd) for c in coords]


def load(name):
    return json.loads((DADOS / name).read_text(encoding="utf-8"))["features"]


# relatórios PDF (só PE)
rel_dir = SITE / "relatorios"
rel_dir.mkdir(exist_ok=True)
pdf_by_code = {}
for d in CONIAPE.iterdir():
    q = d / "quantitativos.json"
    if not (d.is_dir() and q.exists()):
        continue
    code = str(json.loads(q.read_text(encoding="utf-8"))["code"])
    pdfs = list(d.glob("Relatorio_*_PE.pdf"))
    if code.startswith("26") and pdfs:
        shutil.copy2(pdfs[0], rel_dir / pdfs[0].name)
        pdf_by_code[code] = pdfs[0].name

mun = []
for f in load("web_municipios.geojson"):
    p = f["properties"]
    mun.append({
        "c": p["CD_MUN"], "n": p["NM_MUN"], "rgi": p["NM_RGI"], "rgint": p["NM_RGINT"],
        "co": p["CONIAPE"] == "Sim", "aI": p["AREA_IBGE"], "aU": p["AREA_UTM"],
        "urb": p["AREA_URB"], "rur": p["AREA_RUR"], "vias": p["VIAS_KM"],
        "perc": p["PERC_URB"], "dens": p["DENS_VIAS"], "set": p["SETORES"],
        "dist": p["DISTRITOS"], "fonte": p["FONTE"], "pdf": pdf_by_code.get(p["CD_MUN"]),
        "g": {"type": f["geometry"]["type"], "coordinates": rnd(f["geometry"]["coordinates"], 4)},
    })

urb = [{"c": f["properties"]["CD_MUN"], "n": f["properties"]["NOME"],
        "a": f["properties"]["AREA_KM2"],
        "g": {"type": f["geometry"]["type"], "coordinates": rnd(f["geometry"]["coordinates"], 5)}}
       for f in load("web_urb.geojson")]

# vias: agrupadas por município, nomes deduplicados, coordenadas planas com 5 casas
names, name_idx, vias = [], {}, {}
for f in load("web_vias.geojson"):
    p, g = f["properties"], f["geometry"]
    if not g:
        continue
    nm = p["NOME_VIA"] or ""
    if nm not in name_idx:
        name_idx[nm] = len(names); names.append(nm)
    parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
    for part in parts:
        flat = []
        for x, y in (pt[:2] for pt in part):
            flat += [round(x, 5), round(y, 5)]
        vias.setdefault(p["CD_MUN"], []).append([name_idx[nm], round(p["COMP_KM"], 3), flat])

distritos = json.loads((DADOS / "distritos.json").read_text(encoding="utf-8"))

data = {"mun": mun, "urb": urb, "viaNames": names, "vias": vias, "distritos": distritos,
        "gerado": __import__("datetime").date.today().isoformat()}
js = "window.CONIAPE_DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"
(SITE / "data.js").write_text(js, encoding="utf-8")
print("data.js", round(len(js.encode()) / 1e6, 2), "MB |", len(mun), "municipios |",
      sum(1 for m in mun if m["co"]), "CONIAPE |", len(pdf_by_code), "PDFs")
