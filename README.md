# CONIAPE · Mapa dos municípios de Pernambuco

Mapa interativo com área urbana (setores IBGE 2022, CD_SIT 1–3) e extensão de vias urbanas (OpenStreetMap) dos 40 municípios de PE atendidos pelo CONIAPE, sobre a malha municipal IBGE 2024.

- `index.html`: o mapa (Leaflet + jsPDF)
- `data.js`: geometrias e quantitativos (gerado por `build/build_data.py`)
- `relatorios/`: relatórios oficiais em PDF, um por município (Ipojuca não tem)

## Download de relatórios
Ao clicar em **Baixar relatório**, o usuário escolhe entre:
1. **Relatório oficial CONIAPE**: o PDF de `relatorios/`, buscado por `fetch` em `PDF_BASE_URL` (vazio = mesma pasta/site);
2. **Relatório do mapa**: PDF gerado no navegador (indicadores, distritos e mapa vetorial do município).

O botão **Relatório geral** gera um PDF com os 40 municípios e os totais.

## Atualizar os dados
1. `python -I build/prep_coniape.py`: lê os `quantitativos.json` das pastas do CONIAPE
2. Reprocessar no QGIS (join com a malha IBGE, reprojeção para EPSG:31985, exportação dos `web_*.geojson`)
3. `python -I build/build_data.py`: regenera `data.js` e copia os PDFs
