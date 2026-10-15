# CONIAPE · Mapa dos municípios de Pernambuco

Mapa interativo com a área urbana (setores IBGE 2022, CD_SIT 1–3) e as **vias transitáveis por veículo dentro das manchas urbanas** (OpenStreetMap) dos 39 municípios de PE atendidos pelo CONIAPE, sobre a malha municipal IBGE 2024. É a base de quantitativos do mapeamento 360°.

**Mapa:** https://montieur.github.io/coniape-mapa-pe/ · **Manual de uso:** [MANUAL.md](MANUAL.md)

| | |
|---|---|
| Municípios | 39 |
| Área urbana | 430,9 km² |
| Vias transitáveis | 6.476,5 km (critério CONIAPE original: 7.776,5 km) |
| Projeção dos dados | SIRGAS 2000 / UTM 25S (EPSG:31985) |

## Conteúdo

- `index.html`, `relatorio.js`, `data.js`: o mapa (Leaflet + jsPDF); o `data.js` é gerado por `build/build_data.py`
- `dados/`: pacote para download (GeoPackage, shapefile, CSVs de quantitativos, auditoria e revisões)
- `relatorios/`: relatórios oficiais do CONIAPE em PDF, um por município. **Usam o critério antigo de vias.**
- `build/`: scripts de processamento e publicação ([veja o manual](MANUAL.md#parte-4-atualizar-e-publicar-manutenção))

Dados: IBGE · © colaboradores OpenStreetMap (ODbL) · CONIAPE · TECGEO
