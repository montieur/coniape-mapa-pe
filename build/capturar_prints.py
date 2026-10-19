"""Gera os prints do manual (docs/img) e o PDF do manual (dados/Manual_GIS_Comercial.pdf) com o Edge headless.

Uso: com o site servido localmente (python -m http.server 8791 na pasta 03_mapa_html):
     python -I capturar_prints.py [http://localhost:8791]
Os estados da tela vêm dos parâmetros de URL do mapa (?mun=, ?ind=, ?zoom=, ?baixar, ?manual).
"""
import subprocess, sys, tempfile
from pathlib import Path
from urllib.parse import quote

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8791"
SITE = Path(__file__).resolve().parent.parent
IMG = SITE / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

DESK, CEL = (1366, 768), "celular"
PRINTS = [   # arquivo, URL, tamanho da janela (ou "celular": moldura de 390 x 844 px)
    ("01_visao_geral.png", "/", DESK),
    ("02_indicador_densidade.png", "/?ind=dens", DESK),
    ("03_detalhe_municipio.png", "/?mun=2604106", DESK),
    ("04_vias_zoom.png", "/?mun=2604106&zoom=15", DESK),
    ("04b_zoom_mancha.png", "/?mun=2604106&mancha=" + quote("Carapotós (4)"), DESK),
    ("05_baixar_relatorio.png", "/?mun=2601904&baixar", DESK),
    ("06_janela_manual.png", "/?manual", DESK),
    ("07_celular_lista.png", "/", CEL),
    ("08_celular_detalhe.png", "/?mun=2601904", CEL),
    # busca e fontes: usam a simulação do servidor (?mock) para mostrar a tela como ela fica com o servidor ativo
    ("11_busca_municipio.png", "/?mock&q=" + quote("sao bento"), DESK),
    ("12_gerar_dados.png", "/?mock&pesquisa=2606408", DESK),
    ("13_fontes_atualizado.png", "/?mock&mun=2604106", DESK),
    ("14_fontes_ha_atualizacao.png", "/?mock=mudou&mun=2604106", DESK),
    ("09_celular_mapa.png", "/?painel=min", CEL),
    ("10_celular_busca.png", "/?painel=max", CEL),
]

def edge(*args):
    with tempfile.TemporaryDirectory() as perfil:   # perfil isolado: não mexe no Edge do usuário
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                        "--force-device-scale-factor=1", "--blink-settings=preferredColorScheme=1",
                        f"--user-data-dir={perfil}", *args], check=True, timeout=180,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for nome, url, tam in PRINTS:
    if tam == CEL:
        w, h = 560, 940
        url = "/build/moldura_celular.html?src=" + quote(url.lstrip("/"), safe="")
    else:
        w, h = tam
    edge(f"--window-size={w},{h}", "--virtual-time-budget=15000", f"--screenshot={IMG / nome}", BASE + url)
    print("print:", nome, (IMG / nome).stat().st_size // 1024, "KB")

pdf = SITE / "dados" / "Manual_GIS_Comercial.pdf"
edge("--virtual-time-budget=20000", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", BASE + "/manual.html")
print("pdf:", pdf.name, pdf.stat().st_size // 1024, "KB")
