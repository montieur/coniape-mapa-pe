"""Lista compacta dos 5.571 municípios do IBGE para a busca do mapa: dados/municipios_ibge.json

Uso: python -X utf8 gerar_lista_municipios.py        (rodar de vez em quando; a lista quase não muda)
Formato: [[codigo, nome, UF], ...] ordenado por nome.
"""
import json
from pathlib import Path

import requests

dest = Path(__file__).resolve().parent.parent / "dados" / "municipios_ibge.json"
r = requests.get("https://servicodados.ibge.gov.br/api/v1/localidades/municipios?view=nivelado&orderBy=nome",
                 headers={"User-Agent": "GIS-Comercial/1.0 (TECGEO)"}, timeout=120)
r.raise_for_status()
lista = [[str(m["municipio-id"]), m["municipio-nome"], m["UF-sigla"]] for m in r.json()]
dest.write_text(json.dumps(lista, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(len(lista), "municípios ->", dest.name, round(dest.stat().st_size / 1024), "KB")
print([m for m in lista if m[1] in ("Gravatá", "Caruaru", "Bezerros")])
