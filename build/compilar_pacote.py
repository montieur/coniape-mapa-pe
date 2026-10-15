"""Compila o pacote de dados publicado em dados/ (rodar depois de build_data.py).

Uso:  python -I compilar_pacote.py
Gera em ../dados:
  CONIAPE_PE_UTM25S_gpkg.zip   GeoPackages (municípios; vias e áreas urbanas), compactados com VACUUM
  CONIAPE_PE_UTM25S_shp.zip    os mesmos dados em shapefile
  quantitativos_municipios.csv um município por linha (área urbana, vias transitáveis, valor original CONIAPE…)
  quantitativos_manchas.csv    uma mancha urbana por linha
  auditoria_vias_osm.csv / _resumo.md, revisoes.json
"""
import csv, json, shutil, sqlite3, tempfile, zipfile
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
MP = SITE.parent
SHAPES, DADOS = MP / "02_shape_utm", MP / "01_dados"
OUT = SITE / "dados"
OUT.mkdir(exist_ok=True)

# GeoPackages: copia + VACUUM na cópia (o original pode estar aberto no QGIS)
with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(OUT / "CONIAPE_PE_UTM25S_gpkg.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for g in sorted(SHAPES.glob("*.gpkg")):
        dst = Path(tmp) / g.name
        src = sqlite3.connect(f"file:{g}?mode=ro", uri=True); cp = sqlite3.connect(dst)
        src.backup(cp); src.close()
        cp.execute("VACUUM"); cp.close()
        z.write(dst, g.name)

with zipfile.ZipFile(OUT / "CONIAPE_PE_UTM25S_shp.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted((SHAPES / "shp").iterdir()):
        z.write(f, f.name)

# quantitativos (";" e vírgula decimal: abre direto no Excel em português)
br = lambda v: str(v).replace(".", ",") if isinstance(v, float) else ("" if v is None else v)
revs = json.loads((DADOS / "revisoes.json").read_text(encoding="utf-8"))
db = sqlite3.connect(f"file:{SHAPES / 'PE_Municipios_CONIAPE_UTM25S.gpkg'}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
tab = db.execute("select table_name from gpkg_contents where data_type='features'").fetchone()[0]
linhas = db.execute(f'select * from "{tab}" where CONIAPE = "Sim" order by NM_MUN').fetchall()

with open(OUT / "quantitativos_municipios.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["cd_mun", "municipio", "regiao_imediata", "territorio_ibge_km2", "area_urbana_km2", "pct_urbano",
                "vias_transitaveis_km", "densidade_vias_km_km2", "vias_coniape_original_km", "nao_transitaveis_excluidas_km",
                "setores_urbanos", "manchas", "data_revisao", "observacao"])
    for r in linhas:
        rv = revs.get(r["CD_MUN"], {})
        w.writerow([br(v) for v in (r["CD_MUN"], r["NM_MUN"], r["NM_RGI"], r["AREA_IBGE"], r["AREA_URB"], r["PERC_URB"],
                    r["VIAS_KM"], r["DENS_VIAS"], rv.get("vias_km_original"),
                    float(round(sum((rv.get("excluidas_km") or {}).values()), 2)), r["SETORES"], r["DISTRITOS"],
                    rv.get("data"), rv.get("motivo", ""))])

with open(OUT / "quantitativos_manchas.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["cd_mun", "municipio", "mancha", "area_km2", "vias_transitaveis_km", "n_trechos"])
    for cd, rv in sorted(revs.items(), key=lambda x: x[1]["municipio"]):
        for m in rv["manchas"]:
            w.writerow([br(v) for v in (cd, rv["municipio"], m["mancha"], float(m["area_km2"]), float(m["vias_km"]), m["n_vias"])])

for nome in ("auditoria_vias_osm.csv", "auditoria_vias_osm_resumo.md", "revisoes.json"):
    shutil.copy2(DADOS / nome, OUT / nome)

for p in sorted(OUT.iterdir()):
    print(f"{p.name:<36} {p.stat().st_size / 1e6:6.2f} MB")
print(len(linhas), "municípios |", round(sum(r["VIAS_KM"] for r in linhas), 2), "km de vias transitáveis")
