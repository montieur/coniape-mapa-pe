"""GIS Comercial · gera os dados de um município (mesmo método dos municípios do CONIAPE).

    python gerar_municipio.py <código IBGE> [--saida arq.json] [--cache pasta]

1. Setores censitários 2022 do IBGE (arquivo da UF) -> manchas urbanas (CD_SIT 1, 2 ou 3), por distrito
2. Vias do OpenStreetMap (Overpass) transitáveis por veículo, só dentro das manchas
3. Recorte das vias nas manchas e medição em UTM (SIRGAS 2000, fuso do município)
4. JSON no formato que o mapa lê, com a procedência de cada fonte (para a verificação de atualização)
"""
import argparse, json, math, sys, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import requests
from pyproj import Transformer
from shapely import STRtree
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, box, mapping
from shapely.ops import transform, unary_union

VERSAO = 1
UA = {"User-Agent": "GIS-Comercial/1.0 (TECGEO; geoprocessamento)"}
IBGE_SETORES = ("https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
                "malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/gpkg/UF")
IBGE_API = "https://servicodados.ibge.gov.br/api"
# servidores públicos do Overpass oscilam (o principal chegou a ficar fora do ar): tenta vários, em rodízio
OVERPASS = ("https://overpass.openstreetmap.fr/api/interpreter", "https://z.overpass-api.de/api/interpreter",
            "https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter")
# vias que um veículo percorre (mesmo conjunto usado nos 39 municípios revisados)
TIPOS = ("motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|"
         "tertiary|tertiary_link|unclassified|residential|living_street|service|road|track")
TAGS = ("highway", "name", "service", "access", "motor_vehicle", "vehicle")
TILE = 0.05          # graus (~5,5 km): cada consulta ao Overpass cobre um quadrado deste tamanho
MIN_MANCHA_M2 = 200  # descarta migalhas de polígono


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, file=sys.stderr, flush=True)


def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# ------------------------------------------------------------------ IBGE
def meta_ibge(cd):
    r = requests.get(f"{IBGE_API}/v1/localidades/municipios/{cd}", headers=UA, timeout=60)
    r.raise_for_status()
    j = r.json()
    if not j:
        raise ValueError(f"Município {cd} não existe no IBGE")
    j = j[0] if isinstance(j, list) else j
    ri = j.get("regiao-imediata") or {}
    rint = ri.get("regiao-intermediaria") or {}
    uf = (rint.get("UF") or {}).get("sigla") or j["microrregiao"]["mesorregiao"]["UF"]["sigla"]
    return {"nome": j["nome"], "uf": uf, "rgi": ri.get("nome", ""), "rgint": rint.get("nome", "")}


def area_oficial(cd):
    """Área territorial oficial (km²) pela API de agregados do IBGE; None se a API não responder."""
    try:
        r = requests.get(f"{IBGE_API}/v3/agregados/1301/periodos/-1/variaveis/615?localidades=N6[{cd}]",
                         headers=UA, timeout=60)
        s = r.json()[0]["resultados"][0]["series"][0]["serie"]
        return float(list(s.values())[-1])
    except Exception:
        return None


def baixar_setores(uf, cache):
    """Arquivo de setores da UF (reaproveita o do cache se tiver o mesmo tamanho e data)."""
    url = f"{IBGE_SETORES}/{uf}/{uf}_setores_CD2022.gpkg"
    h = requests.head(url, headers=UA, timeout=60, allow_redirects=True)
    h.raise_for_status()
    fonte = {"url": url, "last_modified": h.headers.get("Last-Modified"),
             "content_length": int(h.headers["Content-Length"]), "etag": h.headers.get("ETag")}
    dest = Path(cache) / f"{uf}_setores_CD2022.gpkg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    meta = dest.with_suffix(".meta.json")
    if dest.exists() and dest.stat().st_size == fonte["content_length"] and meta.exists() \
            and json.loads(meta.read_text()).get("last_modified") == fonte["last_modified"]:
        log(f"setores {uf}: usando o arquivo em cache ({dest.stat().st_size / 1e6:.0f} MB)")
        return dest, fonte
    log(f"setores {uf}: baixando {fonte['content_length'] / 1e6:.0f} MB")
    for t in range(6):
        try:
            ja = dest.stat().st_size if dest.exists() else 0
            if ja == fonte["content_length"]:
                break                      # já completo (ex.: baixado antes, sem o registro de data)
            if ja > fonte["content_length"]:
                dest.unlink(); ja = 0
            cab = dict(UA, Range=f"bytes={ja}-") if ja else UA
            with requests.get(url, headers=cab, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(dest, "ab" if ja else "wb") as f:
                    for bloco in r.iter_content(1 << 20):
                        f.write(bloco)
            if dest.stat().st_size == fonte["content_length"]:
                break
        except requests.RequestException as e:
            log("  falhou:", e, "- tentando de novo"); time.sleep(5 * (t + 1))
    else:
        raise RuntimeError("Não consegui baixar os setores do IBGE")
    meta.write_text(json.dumps(fonte))
    return dest, fonte


# ------------------------------------------------------------------ geometria
def epsg_utm(lon):
    zona = min(25, max(18, int((lon + 180) // 6) + 1))   # SIRGAS 2000 / UTM 18S..25S = EPSG 31978..31985
    return 31960 + zona


def arredondar(coords, nd):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], nd), round(coords[1], nd)]
    return [arredondar(c, nd) for c in coords]


def poligonos(g):
    return [g] if isinstance(g, Polygon) else [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon)]


def partes_linha(g):
    if g.is_empty:
        return []
    if isinstance(g, LineString):
        return [g]
    if isinstance(g, MultiLineString) or hasattr(g, "geoms"):
        return [p for x in g.geoms for p in partes_linha(x)]
    return []


def manchas_urbanas(urb_utm):
    """Uma mancha por componente contínuo de setores urbanos de cada distrito, da maior para a menor."""
    saida = []
    for (_cd, nome), sub in urb_utm.groupby(["CD_DIST", "NM_DIST"], sort=True):
        u = unary_union(list(sub.geometry)).buffer(1).buffer(-1)   # fecha frestas de ~1 m entre setores
        partes = sorted([p for p in poligonos(u) if p.area >= MIN_MANCHA_M2], key=lambda p: -p.area)
        for i, p in enumerate(partes, 1):
            saida.append({"nome": nome if len(partes) == 1 else f"{nome} ({i})", "geom": p})
    return saida


# ------------------------------------------------------------------ OpenStreetMap
def overpass(consulta, tentativas=5):
    ultimo = None
    for t in range(tentativas):
        for ep in OVERPASS:
            try:
                r = requests.post(ep, data={"data": consulta}, headers=UA, timeout=(15, 200))   # (conexão, leitura)
                if r.status_code == 200:
                    return r.json(), ep
                ultimo = f"HTTP {r.status_code} em {ep}"
            except (requests.RequestException, ValueError) as e:
                ultimo = f"{type(e).__name__} em {ep}"
        log("  overpass:", ultimo, "- aguardando"); time.sleep(10 * (t + 1))
    raise RuntimeError(f"Overpass indisponível ({ultimo})")


def tiles_das_manchas(manchas_wgs):
    """Quadrados de TILE graus que tocam alguma mancha (evita consultar o vazio entre manchas distantes)."""
    achados = set()
    for m in manchas_wgs:
        w, s, e, n = m.bounds
        for i in range(math.floor(w / TILE), math.floor(e / TILE) + 1):
            for j in range(math.floor(s / TILE), math.floor(n / TILE) + 1):
                if box(i * TILE, j * TILE, (i + 1) * TILE, (j + 1) * TILE).intersects(m):
                    achados.add((i, j))
    return sorted(achados)


def baixar_vias(manchas_wgs):
    tiles = tiles_das_manchas(manchas_wgs)
    log(f"vias OSM: {len(tiles)} consulta(s) ao Overpass")
    vias, bases, ep_usado = {}, [], None
    for k, (i, j) in enumerate(tiles, 1):
        s, w, n, e = j * TILE, i * TILE, (j + 1) * TILE, (i + 1) * TILE
        q = f'[out:json][timeout:180];way["highway"~"^({TIPOS})$"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});out tags geom;'
        dados, ep_usado = overpass(q)
        bases.append((dados.get("osm3s") or {}).get("timestamp_osm_base"))
        for el in dados.get("elements", []):
            if el.get("geometry"):
                vias[el["id"]] = el
        log(f"  tile {k}/{len(tiles)}: {len(dados.get('elements', []))} vias")
        time.sleep(1.2)
    bases = [b for b in bases if b]
    return vias, {"base": min(bases) if bases else None, "consultado_em": agora(), "endpoint": ep_usado,
                  "tiles": len(tiles), "vias_total": len(vias), "bbox": [round(min(m.bounds[0] for m in manchas_wgs), 5),
                                                round(min(m.bounds[1] for m in manchas_wgs), 5),
                                                round(max(m.bounds[2] for m in manchas_wgs), 5),
                                                round(max(m.bounds[3] for m in manchas_wgs), 5)]}


def motivo_exclusao(t):
    if t.get("access") in ("private", "no"):
        return "acesso privado/proibido"
    if t.get("motor_vehicle") in ("no", "private") or t.get("vehicle") in ("no", "private"):
        return "proibido a veículos"
    if t.get("service") in ("driveway", "parking_aisle", "drive-through"):
        return f"service={t['service']}"
    return None


# ------------------------------------------------------------------ geração
def gerar(cd, cache, saida=None):
    cd = str(cd).zfill(7)
    meta = meta_ibge(cd)
    log(f"{meta['nome']} - {meta['uf']} ({cd})")
    gpkg, fonte_setores = baixar_setores(meta["uf"], cache)

    setores = gpd.read_file(gpkg, where=f"CD_MUN = '{cd}'", engine="pyogrio")
    if setores.empty:
        raise ValueError("Nenhum setor censitário encontrado para este município")
    lon_c = float(setores.geometry.union_all().centroid.x)
    epsg = epsg_utm(lon_c)
    s_utm = setores.to_crs(epsg)
    to_wgs = Transformer.from_crs(epsg, 4326, always_xy=True).transform
    to_utm = Transformer.from_crs(4326, epsg, always_xy=True).transform

    urb = s_utm[s_utm["CD_SIT"].isin(["1", "2", "3"])]
    rur = s_utm[~s_utm["CD_SIT"].isin(["1", "2", "3"])]
    territorio = unary_union(list(s_utm.geometry)).buffer(1).buffer(-1)
    manchas = manchas_urbanas(urb)
    log(f"{len(urb)} setores urbanos -> {len(manchas)} mancha(s); {len(rur)} rurais")
    if not manchas:
        raise ValueError("O município não tem setores urbanos (CD_SIT 1, 2 ou 3)")

    polys_utm = [m["geom"] for m in manchas]
    polys_wgs = [transform(to_wgs, p) for p in polys_utm]
    uniao_utm = unary_union(polys_utm)
    arvore = STRtree(polys_utm)

    vias_osm, fonte_osm = baixar_vias(polys_wgs)

    nomes, idx_nome = [], {}
    segs = []                                  # [índice do nome, km, [x,y,x,y...]]
    km_mancha, n_mancha = defaultdict(float), defaultdict(int)
    km_tipo, excl = defaultdict(float), defaultdict(float)
    for el in vias_osm.values():
        tags = el.get("tags") or {}
        linha = transform(to_utm, LineString([(p["lon"], p["lat"]) for p in el["geometry"]]))
        motivo = motivo_exclusao(tags)
        for k in arvore.query(linha, predicate="intersects"):
            for parte in partes_linha(linha.intersection(polys_utm[k])):
                km = parte.length / 1000
                if km <= 0:
                    continue
                if motivo:
                    excl[motivo] += km
                    continue
                nome = tags.get("name") or tags.get("highway") or ""
                if nome not in idx_nome:
                    idx_nome[nome] = len(nomes); nomes.append(nome)
                flat = []
                for x, y in transform(to_wgs, parte).coords:
                    flat += [round(x, 5), round(y, 5)]
                segs.append([idx_nome[nome], round(km, 3), flat])
                km_mancha[manchas[k]["nome"]] += km; n_mancha[manchas[k]["nome"]] += 1
                km_tipo[tags.get("highway", "")] += km

    vias_km = sum(km_mancha.values())
    area_urb = uniao_utm.area / 1e6
    area_rur = sum(g.area for g in rur.geometry) / 1e6
    area_terr = territorio.area / 1e6
    a_ibge = area_oficial(cd) or float(setores["AREA_KM2"].sum())
    log(f"urbana {area_urb:.2f} km2 | vias {vias_km:.2f} km | {len(segs)} trechos")

    contorno = transform(to_wgs, territorio.simplify(40))
    resultado = {
        "versao": VERSAO, "gerado_em": agora(),
        "mun": {
            "c": cd, "n": meta["nome"], "uf": meta["uf"], "rgi": meta["rgi"], "rgint": meta["rgint"],
            "co": False, "origem": "pesquisa",
            "aI": round(a_ibge, 3), "aU": round(area_terr, 3), "urb": round(area_urb, 2), "rur": round(area_rur, 2),
            "vias": round(vias_km, 2), "perc": round(area_urb / a_ibge * 100, 2),
            "dens": round(vias_km / area_urb, 2) if area_urb else None,
            "set": int(len(urb)), "dist": len(manchas), "pdf": None,
            "fonte": "IBGE setores 2022 + vias OSM transitáveis (gerado pelo GIS Comercial)",
            "g": {"type": contorno.geom_type, "coordinates": arredondar(mapping(contorno)["coordinates"], 4)},
        },
        "urb": [{"c": cd, "n": m["nome"], "a": round(m["geom"].area / 1e6, 4),
                 "g": {"type": "Polygon", "coordinates": arredondar(mapping(transform(to_wgs, m["geom"]))["coordinates"], 5)}}
                for m in manchas],
        "viaNames": nomes, "vias": segs,
        "distritos": [{"CD_MUN": cd, "municipio": meta["nome"], "distrito": m["nome"],
                       "area_km2": round(m["geom"].area / 1e6, 2), "vias_km": round(km_mancha[m["nome"]], 2)}
                      for m in manchas],
        "por_tipo_km": {k: round(v, 2) for k, v in sorted(km_tipo.items(), key=lambda x: -x[1])},
        "excluidas_km": {k: round(v, 2) for k, v in excl.items()},
        "crs_medicao": f"EPSG:{epsg}",
        "fontes": {"ibge_setores": dict(fonte_setores, baixado_em=agora()), "osm": fonte_osm,
                   "criterio": "Vias transitáveis por veículo (OSM), recortadas nas manchas urbanas IBGE 2022 (CD_SIT 1-3)"},
    }
    if saida:
        Path(saida).parent.mkdir(parents=True, exist_ok=True)
        Path(saida).write_text(json.dumps(resultado, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        log(f"gravado: {saida} ({Path(saida).stat().st_size / 1e3:.0f} KB)")
    return resultado


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("codigo")
    ap.add_argument("--saida")
    ap.add_argument("--cache", default=str(Path(__file__).resolve().parent / ".cache"))
    a = ap.parse_args()
    r = gerar(a.codigo, a.cache, a.saida)
    m = r["mun"]
    print(json.dumps({k: m[k] for k in ("n", "uf", "aI", "urb", "vias", "dens", "dist")}, ensure_ascii=False))
    for d in r["distritos"]:
        print(f"  {d['distrito']:<28} {d['area_km2']:>7} km2 {d['vias_km']:>9} km")
