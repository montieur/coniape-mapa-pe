"""Teste de ponta a ponta do processador de fila, sem Supabase: sobe um servidor falso que imita o que o
processar_fila.py usa (PostgREST + Storage) e roda um pedido de verdade.

    python -X utf8 teste_fila_local.py <código IBGE> [pasta de cache dos setores]
"""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PORTA = 8899
PEDIDOS = {}
MUNICIPIOS = {}
STORAGE = {}
LOCK = threading.Lock()


def filtros(qs):
    return {k: v[0] for k, v in qs.items() if k not in ("select", "order", "limit", "on_conflict")}


def casa(linha, f):
    for k, v in f.items():
        op, _, val = v.partition(".")
        if op == "eq" and str(linha.get(k)) != val:
            return False
        if op == "lt" and not (linha.get(k) and str(linha[k]) < val):
            return False
    return True


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _resp(self, codigo, corpo=None):
        dados = json.dumps(corpo).encode() if corpo is not None else b""
        self.send_response(codigo); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados))); self.end_headers(); self.wfile.write(dados)

    def _tab(self, nome):
        return {"gc_pedidos": PEDIDOS, "gc_municipios": MUNICIPIOS}[nome]

    def _corpo(self):
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n)

    def do_GET(self):
        u = urlparse(self.path); qs = parse_qs(u.query)
        tab = self._tab(u.path.split("/")[-1])
        with LOCK:
            linhas = [dict(l) for l in tab.values() if casa(l, filtros(qs))]
        if "order" in qs:
            linhas.sort(key=lambda l: l.get("criado_em", ""))
        if "limit" in qs:
            linhas = linhas[:int(qs["limit"][0])]
        self._resp(200, linhas)

    def do_PATCH(self):
        u = urlparse(self.path); qs = parse_qs(u.query)
        tab = self._tab(u.path.split("/")[-1]); novo = json.loads(self._corpo())
        with LOCK:
            alvo = [l for l in tab.values() if casa(l, filtros(qs))]
            for l in alvo:
                l.update(novo)
            saida = [dict(l) for l in alvo]
        self._resp(200, saida if "return=representation" in self.headers.get("Prefer", "") else None)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path.startswith("/storage/v1/object/gc-municipios/"):
            STORAGE[u.path.split("/")[-1]] = self._corpo()
            return self._resp(200, {"Key": u.path})
        tab = self._tab(u.path.split("/")[-1]); linha = json.loads(self._corpo())
        with LOCK:
            tab[linha.get("id") or linha["cd_mun"]] = linha
        self._resp(201)


if __name__ == "__main__":
    cd = sys.argv[1]
    cache = sys.argv[2] if len(sys.argv) > 2 else str(Path(__file__).resolve().parent / ".cache")
    srv = ThreadingHTTPServer(("127.0.0.1", PORTA), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    PEDIDOS["p1"] = {"id": "p1", "cd_mun": cd, "tipo": "gerar", "status": "fila", "tentativas": 0,
                     "criado_em": "2026-10-19T00:00:00Z"}
    env = dict(os.environ, SUPABASE_URL=f"http://127.0.0.1:{PORTA}", SUPABASE_SERVICE_KEY="chave-de-teste", GC_CACHE=cache)
    r = subprocess.run([sys.executable, "-X", "utf8", "-u", str(Path(__file__).resolve().parent / "processar_fila.py")],
                       env=env, cwd=Path(__file__).resolve().parent)
    print("\n== resultado do teste ==")
    print("saída do processo:", r.returncode)
    print("pedido:", {k: v for k, v in PEDIDOS["p1"].items() if k != "ip_hash"})
    m = MUNICIPIOS.get(cd)
    print("município gravado:", bool(m), "|", m and {k: m[k] for k in ("nome", "uf", "origem", "arquivo")}, "| resumo:", m and m["resumo"])
    print("arquivo no storage:", {k: f"{len(v) / 1e3:.0f} KB" for k, v in STORAGE.items()})
    if STORAGE:
        out = Path(cache).parent / f"teste_{cd}.json"      # ao lado da pasta de cache dos setores
        out.write_bytes(next(iter(STORAGE.values()))); print("cópia para teste da tela:", out)
