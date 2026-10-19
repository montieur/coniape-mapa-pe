"""GIS Comercial · confere se as fontes de um município mudaram desde que ele foi gerado.

Mesma lógica de supabase/functions/_shared/verificar.ts. Roda aqui (na automação do GitHub) porque os servidores
do Overpass recusam o ambiente das Edge Functions do Supabase, mas respondem às máquinas do GitHub.

  - IBGE: compara a data (Last-Modified) e o tamanho do arquivo de setores com os registrados na geração
  - OSM: pergunta ao Overpass quantas vias transitáveis mudaram na área desde a data da extração (filtro newer)
"""
from datetime import datetime, timedelta, timezone

import requests

from gerar_municipio import OVERPASS, TIPOS, UA, agora, log

RECIFE = timezone(timedelta(hours=-3))   # sem horário de verão


def data_br(iso):
    if not iso:
        return "?"
    d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    return d.astimezone(RECIFE).strftime("%d/%m/%Y")


def checar_ibge(f):
    if not f or not f.get("url"):
        return {"mudou": None, "gerado": None, "atual": None, "erro": "fonte do IBGE não registrada"}
    try:
        r = requests.head(f["url"], headers=UA, timeout=30, allow_redirects=True)
        if not r.ok:
            return {"mudou": None, "gerado": f.get("last_modified"), "atual": None, "erro": f"HTTP {r.status_code}"}
        lm, tam = r.headers.get("Last-Modified"), int(r.headers.get("Content-Length") or 0)
        mudou_data = bool(f.get("last_modified") and lm and
                          datetime.strptime(lm, "%a, %d %b %Y %H:%M:%S %Z") != datetime.strptime(f["last_modified"], "%a, %d %b %Y %H:%M:%S %Z"))
        mudou_tam = bool(f.get("content_length") and tam and tam != f["content_length"])
        return {"mudou": mudou_data or mudou_tam, "gerado": f.get("last_modified"), "atual": lm}
    except (requests.RequestException, ValueError) as e:
        return {"mudou": None, "gerado": f.get("last_modified"), "atual": None, "erro": str(e)[:120]}


def checar_osm(f):
    if not f or not f.get("base") or not f.get("bbox"):
        return {"mudou": None, "vias_alteradas": None, "desde": None, "erro": "extração do OSM não registrada"}
    w, s, e, n = f["bbox"]
    q = f'[out:json][timeout:60];way["highway"~"^({TIPOS})$"](newer:"{f["base"]}")({s},{w},{n},{e});out count;'
    ultimo = ""
    for tentativa in range(2):
        for ep in OVERPASS:
            try:
                r = requests.post(ep, data={"data": q}, headers=UA, timeout=(15, 90))
                if r.status_code != 200:
                    ultimo = f"HTTP {r.status_code} em {ep.split('/')[2]}"
                    continue
                total = int(r.json()["elements"][0]["tags"]["ways"])
                pct = round(total / f["vias_total"] * 1000) / 10 if f.get("vias_total") else None
                return {"mudou": total > 0, "vias_alteradas": total, "desde": f["base"], "percentual": pct}
            except (requests.RequestException, ValueError, KeyError, IndexError) as err:
                ultimo = f"{type(err).__name__} em {ep.split('/')[2]}"
        log("  conferência OSM:", ultimo, "- tentando de novo")
    return {"mudou": None, "vias_alteradas": None, "desde": f["base"], "erro": f"Overpass indisponível ({ultimo})"}


def resumir(ibge, osm, gerado_em, base_osm):
    desde = data_br(gerado_em or base_osm)
    if ibge["mudou"] is True or osm["mudou"] is True:
        partes = []
        if ibge["mudou"]:
            partes.append("os setores censitários do IBGE foram republicados")
        if osm["mudou"]:
            pct = f" ({str(osm['percentual']).replace('.', ',')}% das vias da área)" if osm.get("percentual") is not None else ""
            partes.append(f"{osm['vias_alteradas']} via(s) mudaram no OpenStreetMap na área{pct}")
        return f"Há atualização desde {desde}: {' e '.join(partes)}."
    if ibge["mudou"] is False and osm["mudou"] is False:
        return f"Sem atualização nas fontes desde {desde}. Os dados já estão atualizados."
    return f"Não foi possível confirmar se há atualização ({ibge.get('erro') or osm.get('erro') or 'fonte indisponível'})."


def verificar(fontes, gerado_em=None):
    ibge = checar_ibge(fontes.get("ibge_setores"))
    osm = checar_osm(fontes.get("osm"))
    mudou = True if (ibge["mudou"] is True or osm["mudou"] is True) else (None if (ibge["mudou"] is None or osm["mudou"] is None) else False)
    return {"verificado_em": agora(), "mudou": mudou, "ibge": ibge, "osm": osm,
            "resumo": resumir(ibge, osm, gerado_em, (fontes.get("osm") or {}).get("base"))}


if __name__ == "__main__":   # teste manual: python verificar_fontes.py <pacote.json>
    import json, sys
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    v = verificar(d["fontes"], d.get("gerado_em"))
    print(json.dumps({k: v[k] for k in ("mudou", "resumo")}, ensure_ascii=False))
