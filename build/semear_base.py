"""GIS Comercial · semeia no banco os 39 municípios do CONIAPE que já estão no mapa.

Assim eles passam a existir no servidor como qualquer município gerado: aparecem no catálogo e a conferência
de atualização das fontes (IBGE e OpenStreetMap) funciona para eles também.

    python -X utf8 semear_base.py             # só monta os arquivos em dados/_semente (confira antes de enviar)
    python -X utf8 semear_base.py --enviar    # envia ao Supabase (SUPABASE_URL e SUPABASE_SERVICE_KEY no ambiente)

Entradas: data.js (dados atuais do mapa) e 00_osm_download/*_osm_vias_transitavel.geojson (só o final do arquivo, que
guarda o horário da base do OSM usada na extração).
"""
import argparse
import json
import os
import re
from pathlib import Path

import requests

AQUI = Path(__file__).resolve().parent
SITE = AQUI.parent
MP = SITE.parent
SAIDA = SITE / "dados" / "_semente"
OSM_DIR = MP / "00_osm_download"
IBGE_PE = {
    "url": "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
           "malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/gpkg/UF/PE/PE_setores_CD2022.gpkg",
    "last_modified": "Tue, 12 Nov 2024 20:08:36 GMT",       # arquivo do IBGE usado nas manchas (conferido por HEAD em 19/10/2026)
    "content_length": 43843584,
}
# Caruaru foi extraído por fora da auditoria (e o arquivo dela foi sobrescrito depois): usa o horário do log daquela extração
BASE_OSM_FIXA = {"2604106": "2026-10-15T10:53:36Z"}


def base_osm(pasta, cd):
    if cd in BASE_OSM_FIXA:
        return BASE_OSM_FIXA[cd]
    f = OSM_DIR / f"{pasta}_osm_vias_transitavel.geojson"
    if f.exists():
        with open(f, "rb") as fh:
            fh.seek(max(0, f.stat().st_size - 400))
            m = re.search(rb'"osm_base":\s*"([^"]+)"', fh.read())
            if m:
                return m.group(1).decode()
    return None


def bbox(urbs):
    xs, ys = [], []
    def percorre(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for k in c:
                percorre(k)
    for u in urbs:
        percorre(u["g"]["coordinates"])
    return [round(min(xs), 5), round(min(ys), 5), round(max(xs), 5), round(max(ys), 5)]


def main(enviar):
    t = (SITE / "data.js").read_text(encoding="utf-8")
    D = json.loads(t[t.index("=") + 1:].rstrip().rstrip(";"))
    revs = json.loads((MP / "01_dados" / "revisoes.json").read_text(encoding="utf-8"))
    pastas = {}
    for q in (MP.parent).glob("[0-9][0-9]_*/quantitativos.json"):
        pastas[str(json.loads(q.read_text(encoding="utf-8"))["code"])] = q.parent.name
    SAIDA.mkdir(parents=True, exist_ok=True)

    sem_base = []
    linhas = []
    for m in [x for x in D["mun"] if x["co"]]:
        cd = m["c"]
        rev = revs.get(cd, {})
        urbs = [u for u in D["urb"] if u["c"] == cd]
        nomes, idx, vias = [], {}, []
        for ni, km, flat in D["vias"].get(cd, []):
            nome = D["viaNames"][ni]
            if nome not in idx:
                idx[nome] = len(nomes); nomes.append(nome)
            vias.append([idx[nome], km, flat])
        base = base_osm(pastas.get(cd, ""), cd)
        if not base:
            sem_base.append(m["n"])
        gerado = f"{rev.get('data', '2026-10-15')}T12:00:00Z"
        mun = {k: m[k] for k in ("c", "n", "rgi", "rgint", "aI", "aU", "urb", "rur", "vias", "perc", "dens", "set", "dist", "g")}
        mun.update({"uf": "PE", "co": False, "origem": "coniape", "pdf": m.get("pdf"),
                    "fonte": "CONIAPE (setores IBGE 2022) + vias OSM transitáveis"})
        pacote = {
            "versao": 1, "gerado_em": gerado, "mun": mun, "urb": urbs, "viaNames": nomes, "vias": vias,
            "distritos": [d for d in D["distritos"] if d["CD_MUN"] == cd],
            "por_tipo_km": rev.get("por_tipo_km") or {}, "excluidas_km": rev.get("excluidas_km") or {},
            "crs_medicao": "EPSG:31985",
            "fontes": {"ibge_setores": dict(IBGE_PE), "criterio": rev.get("criterio", ""),
                       # vias_total: trechos medidos (aproxima o nº de vias da área, só para dar a proporção da mudança)
                       "osm": {"base": base or f"{rev.get('data', '2026-10-15')}T00:00:00Z", "bbox": bbox(urbs), "vias_total": len(vias),
                               "consultado_em": gerado, "endpoint": "overpass"}},
        }
        (SAIDA / f"{cd}.json").write_text(json.dumps(pacote, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        linhas.append({
            "cd_mun": cd, "nome": m["n"], "uf": "PE", "rgi": m["rgi"], "rgint": m["rgint"], "origem": "coniape",
            "resumo": {k: m[k] for k in ("aI", "aU", "urb", "rur", "vias", "perc", "dens", "set", "dist")},
            "contorno": m["g"], "fontes": pacote["fontes"], "arquivo": f"{cd}.json", "versao": 1, "gerado_em": gerado,
        })
    print(f"{len(linhas)} municípios montados em {SAIDA}")
    if sem_base:
        print("sem horário exato da base OSM (usou meia-noite do dia):", ", ".join(sem_base))
    print("exemplo:", json.dumps({k: linhas[0][k] for k in ("nome", "resumo")}, ensure_ascii=False)[:160],
          "| base OSM:", linhas[0]["fontes"]["osm"]["base"])
    if not enviar:
        print("\nConfira os arquivos e rode de novo com --enviar para gravar no servidor.")
        return

    url, chave = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"]
    H = {"apikey": chave, "Authorization": f"Bearer {chave}"}
    for ln in linhas:
        cd = ln["cd_mun"]
        corpo = (SAIDA / f"{cd}.json").read_bytes()
        r = requests.post(f"{url}/storage/v1/object/gc-municipios/{cd}.json", data=corpo, timeout=180,
                          headers=dict(H, **{"Content-Type": "application/json", "x-upsert": "true"}))
        r.raise_for_status()
        r = requests.post(f"{url}/rest/v1/gc_municipios?on_conflict=cd_mun", json=ln, timeout=60,
                          headers=dict(H, **{"Prefer": "resolution=merge-duplicates"}))
        r.raise_for_status()
        print("enviado:", ln["nome"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--enviar", action="store_true")
    main(ap.parse_args().enviar)
