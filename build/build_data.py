"""Monta data.js (dados compactos do mapa) e copia os relatórios PDF de PE.

Uso:  python -I build_data.py
Entradas: ../../01_dados/web_*.geojson, distritos.json  (exportados do QGIS)
Saídas:   ../data.js  e  ../relatorios/*.pdf
"""
import hashlib, json, re, shutil
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

# revisões de vias (aplicar_revisao_vias.py): sobrepõem os quantitativos originais
rev_path = DADOS / "revisoes.json"
revs = json.loads(rev_path.read_text(encoding="utf-8")) if rev_path.exists() else {}
for m in mun:
    r = revs.get(m["c"])
    if r:
        m["vias"] = r["vias_km"]
        m["dens"] = round(r["vias_km"] / m["urb"], 2)
        m["fonte"] = "CONIAPE (setores IBGE 2022) + vias OSM revisadas"
        m["rev"] = {"data": r["data"], "orig": r["vias_km_original"], "recort": r["vias_recortadas_km"],
                    "motivo": r["motivo"], "criterio": r.get("criterio", ""), "excl": r.get("excluidas_km") or {}}

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
urb_nomes = {}
for u in urb:
    urb_nomes.setdefault(u["c"], []).append(u["n"])
for cd, r in revs.items():   # manchas remedidas com as vias novas
    nome = r["municipio"]
    def rotulo(x):
        # município de mancha única: a medição usa o nome da pasta ("03_Angelim"); mostra o nome do polígono
        if re.match(r"^\d\d_", x["mancha"]) and len(set(urb_nomes.get(cd, []))) == 1:
            return urb_nomes[cd][0]
        return x["mancha"]
    distritos = [d for d in distritos if d["CD_MUN"] != cd] + [
        {"CD_MUN": cd, "municipio": nome, "distrito": rotulo(x), "area_km2": x["area_km2"],
         "vias_km": x["vias_km"]} for x in r["manchas"]]

data = {"mun": mun, "urb": urb, "viaNames": names, "vias": vias, "distritos": distritos,
        "gerado": __import__("datetime").date.today().isoformat()}
js = "window.CONIAPE_DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"
(SITE / "data.js").write_text(js, encoding="utf-8")

# versão no endereço dos scripts: o navegador não reaproveita um data.js/relatorio.js antigo do cache
idx = SITE / "index.html"
html = idx.read_text(encoding="utf-8")
for nome in ("data.js", "relatorio.js"):
    v = hashlib.sha1((SITE / nome).read_bytes()).hexdigest()[:8]
    html = re.sub(rf'src="{re.escape(nome)}(\?v=\w+)?"', f'src="{nome}?v={v}"', html)
idx.write_text(html, encoding="utf-8")
print("data.js", round(len(js.encode()) / 1e6, 2), "MB |", len(mun), "municipios |",
      sum(1 for m in mun if m["co"]), "CONIAPE |", len(pdf_by_code), "PDFs")
