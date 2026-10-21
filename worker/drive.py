"""GIS Comercial · Google Drive: guarda os arquivos GIS (SHP, KML, KMZ) e mantém a planilha geral.

Autorização: segredo GOOGLE_OAUTH (JSON com client_id, client_secret, refresh_token, token_uri), escopo drive.file.
Com esse escopo o app só enxerga o que ele mesmo criou: cria a pasta raiz "GIS Comercial" no Drive de quem autorizou,
com uma pasta por estado e uma por município.

O compartilhamento é decisão de quem administra: o app NÃO altera permissões. Para os botões de download do mapa
funcionarem para qualquer visitante, a pasta raiz precisa estar com "Qualquer pessoa com o link" (Leitor), feito uma vez
no Drive; os arquivos novos herdam isso da pasta.
"""
import json
import time

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

RAIZ = "GIS Comercial"
PLANILHA = "GIS Comercial - Municípios"
API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3"
SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
PASTA, SHEET = "application/vnd.google-apps.folder", "application/vnd.google-apps.spreadsheet"


def url_arquivo(file_id):
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def url_pasta(folder_id):
    return f"https://drive.google.com/drive/folders/{folder_id}"


class Drive:
    def __init__(self, cfg_json):
        c = json.loads(cfg_json)
        self.cred = Credentials(None, refresh_token=c["refresh_token"], client_id=c["client_id"],
                                client_secret=c["client_secret"], token_uri=c.get("token_uri", "https://oauth2.googleapis.com/token"))
        self._raiz = None

    def _h(self):
        if not self.cred.valid:
            self.cred.refresh(Request())
        return {"Authorization": f"Bearer {self.cred.token}"}

    def _req(self, metodo, url, **kw):
        extra = kw.pop("headers", {})
        for t in range(4):
            r = requests.request(metodo, url, headers=dict(self._h(), **extra), timeout=120, **kw)
            if r.status_code in (429, 500, 502, 503) and t < 3:
                time.sleep(2 ** (t + 1))
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"Drive {metodo} {url.split('?')[0].rsplit('/', 1)[-1]}: HTTP {r.status_code} {r.text[:200]}")
            return r.json() if r.text else {}

    def _achar(self, nome, pai=None, mime=None):
        q = ["trashed=false", "name='" + nome.replace("\\", "\\\\").replace("'", "\\'") + "'"]
        if pai:
            q.append(f"'{pai}' in parents")
        if mime:
            q.append(f"mimeType='{mime}'")
        r = self._req("GET", f"{API}/files", params={"q": " and ".join(q), "fields": "files(id,name)", "pageSize": 10, "orderBy": "createdTime"})
        return (r.get("files") or [None])[0]

    def pasta(self, nome, pai=None):
        f = self._achar(nome, pai, PASTA)
        if f:
            return f["id"]
        meta = {"name": nome, "mimeType": PASTA, **({"parents": [pai]} if pai else {})}
        return self._req("POST", f"{API}/files", params={"fields": "id"}, json=meta)["id"]

    def raiz(self):
        if not self._raiz:
            self._raiz = self.pasta(RAIZ)
        return self._raiz

    def raiz_publica(self):
        perms = self._req("GET", f"{API}/files/{self.raiz()}/permissions", params={"fields": "permissions(type,role)"}).get("permissions", [])
        return any(p["type"] == "anyone" for p in perms)

    def enviar(self, pai, caminho, mime, nome=None):
        """Envia (ou substitui, se já existe um arquivo com o mesmo nome na pasta). Devolve o id."""
        nome = nome or caminho.name
        dados = caminho.read_bytes()
        existente = self._achar(nome, pai)
        if existente:
            self._req("PATCH", f"{UPLOAD}/files/{existente['id']}", params={"uploadType": "media", "fields": "id"},
                      data=dados, headers={"Content-Type": mime})
            return existente["id"]
        meta = {"name": nome, "parents": [pai]}
        corpo = ("--gc\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n" + json.dumps(meta) + "\r\n--gc\r\nContent-Type: " + mime + "\r\n\r\n").encode() \
            + dados + b"\r\n--gc--"
        return self._req("POST", f"{UPLOAD}/files", params={"uploadType": "multipart", "fields": "id"}, data=corpo,
                         headers={"Content-Type": "multipart/related; boundary=gc"})["id"]

    def guardar_municipio(self, uf, nome, cd, arquivos):
        """arquivos: {'shp': Path, 'kmz': Path}. Devolve {'pasta': id, 'shp': id, 'kmz': id}.
        O KML não é mais guardado (o KMZ tem o mesmo conteúdo, compactado): um KML antigo na pasta é apagado."""
        pai = self.pasta(f"{nome} ({cd})", self.pasta(uf, self.raiz()))
        mimes = {"shp": "application/zip", "kmz": "application/vnd.google-earth.kmz"}
        out = {"pasta": pai}
        for k, mime in mimes.items():
            out[k] = self.enviar(pai, arquivos[k], mime)
        self.apagar_kml(pai)
        return out

    def apagar_kml(self, pai=None):
        """Manda para a lixeira do Drive os KML que o app criou (numa pasta ou em todo o Drive do app); ficam 30 dias recuperáveis."""
        q = ["trashed=false", "name contains '.kml'"] + ([f"'{pai}' in parents"] if pai else [])
        n, token = 0, None
        while True:
            r = self._req("GET", f"{API}/files", params={"q": " and ".join(q), "fields": "nextPageToken,files(id,name)", "pageSize": 200,
                                                          **({"pageToken": token} if token else {})})
            for f in r.get("files", []):
                if f["name"].lower().endswith(".kml"):
                    self._req("PATCH", f"{API}/files/{f['id']}", params={"fields": "id"}, json={"trashed": True})
                    n += 1
            token = r.get("nextPageToken")
            if not token:
                return n

    def atualizar_planilha(self, linhas):
        """Reescreve a planilha geral (cabeçalho + uma linha por município)."""
        raiz = self.raiz()
        f = self._achar(PLANILHA, raiz, SHEET)
        if f:
            sid = f["id"]
        else:
            sid = self._req("POST", SHEETS, json={"properties": {"title": PLANILHA}})["spreadsheetId"]
            self._req("PATCH", f"{API}/files/{sid}", params={"addParents": raiz, "removeParents": "root", "fields": "id"})
        aba = self._req("GET", f"{SHEETS}/{sid}", params={"fields": "sheets.properties.title"})["sheets"][0]["properties"]["title"]
        self._req("POST", f"{SHEETS}/{sid}/values/{aba}:clear", json={})
        self._req("PUT", f"{SHEETS}/{sid}/values/{aba}!A1", params={"valueInputOption": "USER_ENTERED"}, json={"values": linhas})
        return sid
