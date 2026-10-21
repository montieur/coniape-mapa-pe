"""Copia os relatórios PDF oficiais (relatorios/) para o Google Drive: GIS Comercial / Relatórios (cópia de segurança).
O mapa continua baixando os PDFs do repositório; o Drive é só a garantia."""
import os
import sys
from pathlib import Path

from drive import Drive

PASTA = Path(__file__).resolve().parent.parent / "relatorios"
d = Drive(os.environ["GOOGLE_OAUTH"])
pai = d.pasta("Relatórios", d.raiz())
pdfs = sorted(PASTA.glob("*.pdf"))
for i, f in enumerate(pdfs, 1):
    d.enviar(pai, f, "application/pdf")
    print(f"{i}/{len(pdfs)} {f.name}", flush=True)
print("pronto:", len(pdfs), "PDFs no Drive")
sys.exit(0)
