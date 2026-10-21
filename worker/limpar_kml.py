"""Manda para a lixeira do Google Drive os KML já guardados e tira a referência a eles do catálogo (gc_municipios.arquivos).
Roda uma vez pelo workflow "Manutenção do Drive" (o KMZ continua: tem o mesmo conteúdo, compactado)."""
import os

import requests

from drive import Drive

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

print("KML enviados à lixeira do Drive:", Drive(os.environ["GOOGLE_OAUTH"]).apagar_kml(), flush=True)
linhas = requests.get(f"{URL}/rest/v1/gc_municipios?select=cd_mun,arquivos&arquivos=not.is.null", headers=H, timeout=60).json()
mudou = 0
for l in linhas:
    a = l["arquivos"]
    if "kml" in (a.get("drive") or {}) or "kml" in (a.get("tamanhos") or {}) or "kml" in a:
        (a.get("drive") or {}).pop("kml", None)
        (a.get("tamanhos") or {}).pop("kml", None)
        a.pop("kml", None)
        requests.patch(f"{URL}/rest/v1/gc_municipios?cd_mun=eq.{l['cd_mun']}", headers=H, json={"arquivos": a}, timeout=60).raise_for_status()
        mudou += 1
print("municípios atualizados no catálogo:", mudou)
