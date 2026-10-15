import csv, json
from pathlib import Path
C = Path(r"C:\Users\tecgeo-jordy\Desktop\CONIAPE"); A = C / "MAPA_PE/01_dados/auditoria_vias"
rows = []
for q in sorted(C.glob("[0-9][0-9]_*/quantitativos.json")):
    Q = json.loads(q.read_text(encoding="utf-8"))
    if not Q["code"].startswith("26"): continue
    p = q.parent.name; m = A / f"{p}_medicao.json"
    if not m.exists(): rows.append({"municipio": Q["name"], "pasta": p, "km_coniape": round(Q["roadsKm"], 2), "status": "sem medição"}); continue
    M = json.loads(m.read_text(encoding="utf-8"))
    orig = {d["nome"]: float(d["vias_km"]) for d in Q.get("districts") or []} or {p: Q["roadsKm"]}
    novo = {r["mancha"]: r["vias_km"] for r in M["manchas"]}
    pares = [(n, orig[n], novo.get(n)) for n in orig]
    falt = [n for n, o, v in pares if v is None]
    pares = [x for x in pares if x[2] is not None]
    pior = max(pares, key=lambda x: abs(x[2] - x[1]))
    batem = sum(abs(v - o) <= max(0.05, .01 * o) for _, o, v in pares)
    k0, k1 = Q["roadsKm"], M["total"]["vias_km"]
    T = A / f"{p}_transitavel.json"
    kt = json.loads(T.read_text(encoding="utf-8"))["total"]["vias_km"] if T.exists() else None
    bases = {}
    for suf in ("_transitavel",):
        g = C / f"MAPA_PE/00_osm_download/{p}_osm_vias{suf}.geojson"
        if g.exists(): bases[suf or "coniape"] = g.read_bytes()[-60:].decode("utf-8", "ignore").split('"osm_base": "')[-1][:10]
    rows.append({"municipio": Q["name"], "pasta": p, "km_coniape": round(k0, 2), "km_osm_atual": k1,
                 "diferenca_pct": round(100 * (k1 - k0) / k0, 1),
                 "km_transitavel_recortado": kt,
                 "transitavel_vs_coniape_pct": round(100 * (kt - k0) / k0, 1) if kt is not None else None,
                 "mancha_maior_diferenca": pior[0], "mancha_km_coniape": round(pior[1], 2), "mancha_km_osm": pior[2],
                 "mancha_diferenca_pct": round(100 * (pior[2] - pior[1]) / pior[1], 1) if pior[1] else None,
                 "manchas_que_batem": f"{batem}/{len(pares)}",
                 "situacao": "candidato à revisão" if abs(k1 - k0) / k0 > .10 else "atenção (5-10%)" if abs(k1 - k0) / k0 > .05 else "bate",
                 "base_osm": " / ".join(sorted(set(bases.values()))),
                 "status": "ok" + (f"; manchas sem par: {falt}" if falt else "")})
cols = ["municipio", "pasta", "km_coniape", "km_osm_atual", "diferenca_pct", "km_transitavel_recortado",
        "transitavel_vs_coniape_pct", "mancha_maior_diferenca", "mancha_km_coniape",
        "mancha_km_osm", "mancha_diferenca_pct", "manchas_que_batem", "situacao", "base_osm", "status"]
with open(C / "MAPA_PE/01_dados/auditoria_vias_osm.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)
for r in sorted(rows, key=lambda r: -(r.get("diferenca_pct") or 0)):
    print(*[r.get(c, "") for c in cols], sep=" | ")
