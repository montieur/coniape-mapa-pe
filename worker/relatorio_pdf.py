"""GIS Comercial · gera o relatório PDF do mapa de cada município no navegador (Chrome sem tela) e guarda no Drive.

É o mesmo código que o botão "Relatório do mapa" executa no site, então o PDF sai idêntico (mapa base, indicadores, distritos).
Cada execução SUBSTITUI o PDF anterior do município (mesmo nome de arquivo na mesma pasta).

Uso:  python relatorio_pdf.py <lista.txt>   (um código IBGE por linha)
      python relatorio_pdf.py --todos       (todos os municípios da base que já estão no Drive)
Variáveis: SUPABASE_URL, SUPABASE_SERVICE_KEY, GOOGLE_OAUTH, GC_SITE (padrão: o site publicado).
"""
import base64
import os
import sys
import tempfile
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

from drive import Drive

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
SITE = os.environ.get("GC_SITE", "https://montieur.github.io/gis-comercial").rstrip("/")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

JS_GERAR = """async (cd) => {
  let saida = null; const original = window.save;
  window.save = (doc, nome) => { saida = {nome, b64: doc.output('datauristring').split(',')[1]}; };
  try { await gerarPdfMunicipio(byCode[cd]); } finally { window.save = original; }
  return saida;
}"""


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def catalogo(codigos=None):
    q = "gc_municipios?select=cd_mun,nome,uf,arquivos&order=uf.asc,nome.asc"
    if codigos:
        q += "&cd_mun=in.(" + ",".join(codigos) + ")"
    r = requests.get(f"{URL}/rest/v1/{q}", headers=H, timeout=60)
    r.raise_for_status()
    return r.json()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--todos":
        alvo = [m for m in catalogo() if (m["arquivos"] or {}).get("drive")]
    else:
        codigos = [l.strip() for l in Path(sys.argv[1]).read_text().splitlines() if l.strip().isdigit()]
        alvo = catalogo(sorted(set(codigos))) if codigos else []
    if not alvo:
        log("nenhum município para gerar PDF")
        return
    drive = Drive(os.environ["GOOGLE_OAUTH"])
    falhas = 0
    with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
        navegador = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
        pagina = navegador.new_page(viewport={"width": 1366, "height": 800})
        pagina.set_default_timeout(180000)
        for i, m in enumerate(alvo, 1):
            cd = m["cd_mun"]
            try:
                pagina.goto(f"{SITE}/?mun={cd}&semconferir&v={int(time.time())}", wait_until="domcontentloaded")
                pagina.wait_for_function("(cd) => typeof byCode !== 'undefined' && byCode[cd] && byCode[cd].detalhe", arg=cd)
                pdf = pagina.evaluate(JS_GERAR, cd)
                if not pdf:
                    raise RuntimeError("o site não devolveu o PDF")
                arq = Path(tmp) / pdf["nome"]
                arq.write_bytes(base64.b64decode(pdf["b64"]))
                pasta = drive.pasta(f"{m['nome']} ({cd})", drive.pasta(m["uf"], drive.raiz()))
                fid = drive.enviar(pasta, arq, "application/pdf")
                a = dict(m["arquivos"] or {})
                a["drive"] = dict(a.get("drive") or {}, pasta=pasta, pdf=fid)
                a.setdefault("tamanhos", {})["pdf"] = arq.stat().st_size
                r = requests.patch(f"{URL}/rest/v1/gc_municipios?cd_mun=eq.{cd}", headers=H, json={"arquivos": a}, timeout=60)
                r.raise_for_status()
                log(f"{i}/{len(alvo)} {m['nome']}: PDF no Drive ({arq.stat().st_size / 1e6:.1f} MB)")
            except Exception as e:  # noqa: BLE001 - um município com problema não interrompe os outros
                falhas += 1
                log(f"{i}/{len(alvo)} {m['nome']}: FALHOU - {str(e)[:200]}")
        navegador.close()
    log(f"relatórios: {len(alvo) - falhas} ok, {falhas} com falha")


if __name__ == "__main__":
    main()
