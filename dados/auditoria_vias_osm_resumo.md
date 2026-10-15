# Auditoria das vias urbanas do CONIAPE x OSM atual — 39 municípios de PE

Data: 15/10/2026 · Base OSM de todos os municípios: 2026-10-15 (overpass-api.de) · Ipojuca fora (outro método).
Tabela completa: `auditoria_vias_osm.csv`. Medições por município: `auditoria_vias/<pasta>_medicao.json` (critério CONIAPE)
e `auditoria_vias/<pasta>_transitavel.json` (critério 360°). Nada foi alterado em shapes, revisoes.json ou no mapa.

## Método
1. Um download por município: `osm_vias_municipio.py <pasta> transitavel`. O filtro CONIAPE (trunk … service) foi extraído
   desse mesmo arquivo (`subset_coniape.py`), porque os tipos dele estão todos contidos no modo transitável. Conferência em Caruaru:
   o subconjunto dá 1.681,13 km, idêntico à revisão.
2. **Critério CONIAPE (via inteira):** reprojeção para EPSG:31985, seleção das vias que tocam `01_area_urbana.kml`
   (`osm_para_utm.py`) e depois `medir_vias_manchas.py`.
3. **Critério 360° (transitável recortado):** `vias_transitaveis_mancha.py`.
4. Situação: |diferença| > 10% = candidato à revisão; de 5 a 10% = atenção; abaixo de 5% = bate.

## Resultado — critério CONIAPE (detecção do corte na extração)
- **Candidato à revisão (> 10%): só Caruaru** (+65,5%; mancha Caruaru (4) 853,97 → 1.448,06 km). Já revisado.
- **Atenção (5–10%), não chegam ao limite:**
  - São Lourenço da Mata: 402,35 → 428,81 km (+6,6%). A mancha principal sobe 7,1% (375,68 → 402,20); a outra mancha bate.
  - Santa Cruz do Capibaribe: 493,76 → 522,89 km (+5,9%). A mancha (2) sobe 5,8% (377,32 → 399,03); 3 de 6 manchas batem.
  Nos dois casos o padrão é o de Caruaru (manchas pequenas batem, a principal cresce), mas em escala bem menor. Pode ser
  mapeamento novo no OSM desde a extração original, e não um corte. Vale uma olhada visual antes de decidir.
- **Batem (36 municípios):** diferença entre −0,5% e +1,3%, quase todos em −0,1%, com todas as manchas batendo. Moreno (+1,3%)
  e São Caitano (−0,5%) são os maiores desvios desse grupo.

Conclusão: o corte na extração foi um problema isolado de Caruaru. Nenhum outro município passa de 10%.

## Critério 360° (transitável recortado nas manchas)
Total dos 39: 6.476,45 km (CONIAPE via inteira: 7.776,54 km; OSM atual via inteira: 8.501,16 km).
Sem Caruaru: 4.975,27 km contra 6.760,50 km do CONIAPE (−26%). Em geral o recorte reduz bastante o km em relação ao
critério CONIAPE: de −1% (São Lourenço da Mata) a −69% (Casinhas), porque estradas que só tocam a mancha deixam de contar
inteiras. A exceção é Caruaru, onde a extração antiga estava incompleta (+47,7%).

## Observação operacional
O Overpass oscilou bastante (502 no servidor principal; kumi e private.coffee devolvendo 500 ou base desatualizada de
junho/julho de 2026). Os municípios que vieram de espelho com base antiga foram baixados de novo só do servidor principal.
Os arquivos `00_osm_download/*_osm_vias.geojson` (modo antigo, sem `transitavel`) de alguns municípios ainda têm base antiga
(Santa Maria do Cambucá, São Benedito do Sul, São Lourenço da Mata, Cumaru, Surubim); eles **não** foram usados na auditoria.
