"""Gera os PNGs do ícone do app a partir de icones/icone.svg (Qt do QGIS: python-qgis-ltr.bat gerar_icones.py)."""
from pathlib import Path
from qgis.PyQt.QtCore import QByteArray, Qt
from qgis.PyQt.QtGui import QGuiApplication, QImage, QPainter
from qgis.PyQt.QtSvg import QSvgRenderer

app = QGuiApplication([])
pasta = Path(__file__).resolve().parent.parent / "icones"
svg = (pasta / "icone.svg").read_text(encoding="utf-8")
# versão "maskable" (Android recorta em círculo/squircle): fundo sem cantos arredondados
variantes = {"": svg, "maskable-": svg.replace('rx="112" ', "")}

for prefixo, fonte in variantes.items():
    r = QSvgRenderer(QByteArray(fonte.encode()))
    for lado in ((512,) if prefixo else (180, 192, 512)):
        im = QImage(lado, lado, QImage.Format_ARGB32); im.fill(Qt.transparent)
        p = QPainter(im); p.setRenderHint(QPainter.Antialiasing); r.render(p); p.end()
        destino = pasta / f"icone-{prefixo}{lado}.png"
        im.save(str(destino)); print(destino.name, destino.stat().st_size // 1024, "KB")
