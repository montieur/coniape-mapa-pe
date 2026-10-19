"""GIS Comercial · processa a fila de pedidos (roda na automação do GitHub a cada 5 minutos).

Variáveis: SUPABASE_URL, SUPABASE_SERVICE_KEY (segredos do repositório; nunca vão para o navegador).
Para cada pedido em 'fila': reserva, gera o município (gerar_municipio.py), grava o JSON no Storage,
atualiza gc_municipios e marca o pedido como 'pronto' (ou 'erro', com a mensagem).
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from gerar_municipio import gerar, log

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
CACHE = os.environ.get("GC_CACHE", str(Path(__file__).resolve().parent / ".cache"))
MAX_PEDIDOS = int(os.environ.get("GC_MAX_PEDIDOS", "6"))
ORCAMENTO_MIN = int(os.environ.get("GC_ORCAMENTO_MIN", "40"))    # para antes de estourar o limite do job
MAX_TENTATIVAS = 3
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}


def agora():
    return datetime.now(timezone.utc)


def rest(metodo, caminho, **kw):
    cab = dict(H, **kw.pop("headers", {}))
    r = requests.request(metodo, f"{URL}/rest/v1/{caminho}", headers=cab, timeout=60, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"{metodo} {caminho}: HTTP {r.status_code} {r.text[:200]}")
    return r.json() if r.text else None


def recuperar_travados():
    """Pedido 'processando' há mais de 40 min = execução anterior caiu: volta para a fila (ou erro)."""
    limite = (agora() - timedelta(minutes=40)).isoformat()
    for p in rest("GET", f"gc_pedidos?status=eq.processando&iniciado_em=lt.{limite}&select=id,tentativas") or []:
        novo = {"status": "fila"} if p["tentativas"] < MAX_TENTATIVAS else \
            {"status": "erro", "mensagem": "A geração não terminou depois de várias tentativas.", "concluido_em": agora().isoformat()}
        rest("PATCH", f"gc_pedidos?id=eq.{p['id']}", json=novo)
        log("pedido travado recolocado:", p["id"], novo["status"])


def reservar():
    fila = rest("GET", "gc_pedidos?status=eq.fila&order=criado_em.asc&limit=1&select=id,cd_mun,tipo,tentativas")
    if not fila:
        return None
    p = fila[0]
    ok = rest("PATCH", f"gc_pedidos?id=eq.{p['id']}&status=eq.fila",
              json={"status": "processando", "iniciado_em": agora().isoformat(), "tentativas": p["tentativas"] + 1},
              headers={"Prefer": "return=representation", "Content-Type": "application/json"})
    return p if ok else None      # lista vazia = outra execução reservou primeiro


def guardar(cd, pacote):
    corpo = json.dumps(pacote, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    r = requests.post(f"{URL}/storage/v1/object/gc-municipios/{cd}.json", data=corpo, timeout=180,
                      headers=dict(H, **{"Content-Type": "application/json", "x-upsert": "true", "Cache-Control": "max-age=300"}))
    if r.status_code >= 400:
        raise RuntimeError(f"Storage: HTTP {r.status_code} {r.text[:200]}")
    m = pacote["mun"]
    anterior = rest("GET", f"gc_municipios?cd_mun=eq.{cd}&select=origem") or []
    linha = {
        "cd_mun": cd, "nome": m["n"], "uf": m["uf"], "rgi": m["rgi"], "rgint": m["rgint"],
        "origem": anterior[0]["origem"] if anterior else "pesquisa",
        "resumo": {k: m[k] for k in ("aI", "aU", "urb", "rur", "vias", "perc", "dens", "set", "dist")},
        "contorno": m["g"],
        "fontes": pacote["fontes"], "arquivo": f"{cd}.json", "versao": pacote["versao"],
        "gerado_em": pacote["gerado_em"], "verificado_em": None, "verificacao": None, "atualizado_em": agora().isoformat(),
    }
    rest("POST", "gc_municipios?on_conflict=cd_mun", json=linha,
         headers={"Prefer": "resolution=merge-duplicates", "Content-Type": "application/json"})


def main():
    inicio = time.time()
    recuperar_travados()
    feitos = 0
    while feitos < MAX_PEDIDOS and (time.time() - inicio) / 60 < ORCAMENTO_MIN:
        p = reservar()
        if not p:
            break
        cd = p["cd_mun"]
        log(f"=== pedido {p['id']}: {p['tipo']} {cd}")
        try:
            pacote = gerar(cd, CACHE)
            guardar(cd, pacote)
            rest("PATCH", f"gc_pedidos?id=eq.{p['id']}", json={
                "status": "pronto", "concluido_em": agora().isoformat(), "mensagem": None},
                 headers={"Content-Type": "application/json"})
            log(f"pronto: {pacote['mun']['n']} - {pacote['mun']['urb']} km2 urbanos, {pacote['mun']['vias']} km de vias")
        except Exception as e:     # noqa: BLE001 - qualquer falha vira mensagem para o usuário
            log("ERRO:", e)
            rest("PATCH", f"gc_pedidos?id=eq.{p['id']}", json={
                "status": "erro" if p["tentativas"] + 1 >= MAX_TENTATIVAS else "fila",
                "mensagem": str(e)[:300], "concluido_em": agora().isoformat()},
                 headers={"Content-Type": "application/json"})
        feitos += 1
    log(f"{feitos} pedido(s) processado(s)")


if __name__ == "__main__":
    sys.exit(main())
