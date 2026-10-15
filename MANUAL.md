# Manual de uso · Mapa CONIAPE Pernambuco

- **Mapa:** https://montieur.github.io/coniape-mapa-pe/ (computador e smartphone)
- **Manual em PDF:** [Manual_CONIAPE_PE.pdf](https://montieur.github.io/coniape-mapa-pe/dados/Manual_CONIAPE_PE.pdf)
- **Repositório:** https://github.com/montieur/coniape-mapa-pe

O mapa mostra, para os **40 municípios de Pernambuco atendidos pelo CONIAPE**, a área urbana e a extensão de **vias transitáveis por veículo dentro das manchas urbanas**, que é a base de quantitativos do mapeamento 360°. Os outros 145 municípios de PE aparecem em cinza só para referência.

- [Parte 1: Usar o mapa](#parte-1-usar-o-mapa)
- [Parte 2: Entender os números](#parte-2-entender-os-números)
- [Parte 3: Baixar os dados](#parte-3-baixar-os-dados)
- [Parte 4: Atualizar e publicar (manutenção)](#parte-4-atualizar-e-publicar-manutenção)

---

## Parte 1: Usar o mapa

### A tela

![Tela inicial do mapa no computador](docs/img/01_visao_geral.png)
*Tela inicial: painel à esquerda, mapa à direita, com os 40 municípios coloridos por km de vias transitáveis.*

| Área | O que tem |
|---|---|
| **Cabeçalho** | Título e os botões **Manual** (esta janela), **Dados** (downloads) e **Relatório geral** (PDF com os 40 municípios) |
| **Resumo** | Totais do CONIAPE em PE: municípios, km² urbanos e km de vias transitáveis |
| **Busca e indicador** | Campo para achar um município e escolha da variável que colore o mapa |
| **Lista** | Municípios ranqueados pelo indicador escolhido, com barra comparativa |
| **Mapa** | Municípios coloridos, áreas urbanas (laranja) e vias (vermelho) |

No smartphone a tela muda ([veja abaixo](#no-smartphone)).

### Escolher o indicador

Em **Indicador**, escolha a variável que colore o mapa e ordena a lista:

- **Vias transitáveis (km)**: extensão de vias para o mapeamento 360°
- **Área urbana (km²)**: soma das manchas urbanas do IBGE
- **Densidade de vias (km/km²)**: km de vias por km² de área urbana
- **Área urbana / território (%)**: quanto do município é urbano

As cores vão de claro (menor) a escuro (maior), em 5 faixas com a mesma quantidade de municípios. Os limites das faixas aparecem na legenda.

![Mapa colorido por densidade de vias](docs/img/02_indicador_densidade.png)
*Indicador "Densidade de vias": a lista passa a ser ranqueada por km/km² e a legenda mostra as novas faixas.*

### Encontrar um município

- **Na lista:** clique no nome. Para ordenar, clique em **Município** (ordem alfabética) ou no cabeçalho do indicador (maior ou menor primeiro).
- **Na busca:** digite parte do nome. Acentos são ignorados, então "sao bento" encontra São Bento do Una.
- **No mapa:** clique dentro do limite do município. Só o limite municipal é clicável; áreas urbanas e vias não interceptam o clique.

Municípios em cinza estão fora do CONIAPE. Ao clicar num deles aparece um aviso.

### O detalhe do município

![Detalhe de Caruaru](docs/img/03_detalhe_municipio.png)
*Caruaru selecionado: contorno forte no mapa, vias em vermelho e o detalhe no painel.*

Ao selecionar um município, o painel mostra:

- **Área urbana** e **vias transitáveis** em destaque, com a posição entre os 40 (ex.: "3º de 40 no CONIAPE")
- **Vias, critério CONIAPE original**: o número antigo, para comparação ([veja a Parte 2](#parte-2-entender-os-números))
- **Não transitáveis excluídas**: km de vias privadas, estacionamentos e garagens que ficaram de fora
- Densidade, % urbano, território (área oficial IBGE e área planimétrica UTM), setores urbanos e número de manchas
- **Distritos e manchas urbanas**: cada mancha com área e km de vias, da maior para a menor. **Clique numa mancha** para aproximar o mapa nela: a mancha ganha um contorno tracejado e a linha fica marcada. Clique de novo na mesma linha para voltar ao município inteiro.

No mapa, o município selecionado ganha contorno forte, os outros ficam esmaecidos e as vias dele aparecem.

![Zoom na mancha Carapotós (4), em Caruaru](docs/img/04b_zoom_mancha.png)
*Clique em "Carapotós (4)" na tabela de manchas: o mapa aproxima na mancha (contorno tracejado) e mostra as vias dela.*

Para voltar à lista, use **Todos os municípios** ou a tecla **Esc**. O botão **Ver no mapa** reenquadra o município.

### Camadas e mapa base

No botão de camadas (canto superior direito do mapa):

- **Mapa base**: Cinza claro (padrão), OpenStreetMap ou Satélite
- **Nomes dos municípios**: aparecem a partir do zoom 9
- **Áreas urbanas**: manchas urbanas do IBGE (laranja)
- **Vias transitáveis**: aparecem com zoom ≥ 11, ou sempre para o município selecionado

![Vias transitáveis no centro de Caruaru](docs/img/04_vias_zoom.png)
*Zoom no centro de Caruaru: cada linha vermelha é um trecho de via transitável dentro da mancha urbana.*

### Baixar relatórios

**Relatório de um município:** no detalhe, clique em **Baixar relatório** e escolha uma opção.

![Janela de escolha do relatório](docs/img/05_baixar_relatorio.png)
*Escolha do relatório de Bezerros: o oficial avisa que usa o critério antigo de vias.*

| Opção | O que é |
|---|---|
| **Relatório oficial CONIAPE** | PDF original do município, baixado do repositório. **Atenção:** traz o km de vias pelo critério antigo do CONIAPE. Ipojuca não tem relatório oficial. |
| **Relatório do mapa** | PDF gerado na hora com mapa base, limite, áreas urbanas, vias, escala, indicadores atuais e tabela de manchas |

**Relatório geral:** o botão no cabeçalho gera um PDF com o mapa de PE e a tabela dos 40 municípios: território, área urbana, vias transitáveis, valor original do CONIAPE, densidade e % urbano, com totais.

Os PDFs são gerados no próprio navegador e precisam de internet para baixar o mapa base. Sem conexão, o PDF sai com fundo liso e um aviso.

### Manual e dados dentro do mapa

O botão **Manual** abre este manual numa janela sobre o mapa, com atalhos para as quatro partes. O botão **Dados** abre a mesma janela já na [Parte 3](#parte-3-baixar-os-dados). Em **Salvar em PDF** você baixa o manual completo, com os prints. Para fechar, use o **×**, a tecla **Esc** ou clique fora da janela.

![Manual aberto dentro do mapa](docs/img/06_janela_manual.png)

### No smartphone

No celular, o mapa ocupa a tela toda e as informações ficam num **painel que desliza de baixo para cima**:

- **Arraste a alça** (o traço no topo do painel) para cima ou para baixo, ou **toque nela** para alternar entre três alturas: recolhido (só os totais, mapa quase inteiro), meio e tela cheia.
- Ao **tocar na busca**, o painel abre em tela cheia para o teclado não cobrir a lista.
- Ao **escolher um município**, o painel vai para o meio: o município aparece enquadrado em cima e o detalhe embaixo.
- A legenda começa recolhida; toque no título dela para abrir.
- No cabeçalho, os botões mostram só os ícones: manual, dados e relatório geral.

<img src="docs/img/07_celular_lista.png" width="260" alt="Celular: mapa e lista"> <img src="docs/img/08_celular_detalhe.png" width="260" alt="Celular: detalhe de Bezerros">

<img src="docs/img/09_celular_mapa.png" width="260" alt="Celular: painel recolhido"> <img src="docs/img/10_celular_busca.png" width="260" alt="Celular: painel em tela cheia">

*Da esquerda para a direita, de cima para baixo: painel no meio com a lista; detalhe de Bezerros; painel recolhido (mapa quase inteiro); painel em tela cheia.*

### Instalar na tela inicial

O mapa pode ser instalado como um aplicativo, com ícone próprio e abrindo em tela cheia, sem a barra do navegador:

| Aparelho | Como instalar |
|---|---|
| **Android (Chrome)** | Abra o endereço do mapa, toque no menu **⋮** e em **Instalar app** (ou **Adicionar à tela inicial**) |
| **iPhone / iPad (Safari)** | Abra o endereço do mapa, toque em **Compartilhar** (quadrado com seta) e em **Adicionar à Tela de Início** |
| **Computador (Chrome / Edge)** | Clique no ícone de instalar, no fim da barra de endereço |

O app instalado usa a internet como o site: os dados ficam sempre atualizados.

### Links diretos

Dá para compartilhar um link que já abre o mapa num estado específico:

| Link | Abre |
|---|---|
| `…/coniape-mapa-pe/?mun=2604106` | Caruaru selecionado (use o código IBGE do município) |
| `…/coniape-mapa-pe/?mun=2604106&zoom=15` | Caruaru com zoom 15 |
| `…/coniape-mapa-pe/?mun=2604106&mancha=Carapotós (4)` | Caruaru com zoom na mancha Carapotós (4) (nome como aparece na tabela) |
| `…/coniape-mapa-pe/?ind=dens` | Mapa colorido por densidade de vias (`vias`, `urb`, `dens` ou `perc`) |
| `…/coniape-mapa-pe/?mun=2601904&baixar` | Bezerros com a janela de relatório aberta |
| `…/coniape-mapa-pe/?manual` | Manual aberto |

---

## Parte 2: Entender os números

### Área urbana

Soma das manchas formadas pelos **setores censitários urbanos do IBGE 2022** (situação CD_SIT 1, 2 ou 3), conforme a extração do CONIAPE. Cada município pode ter várias manchas: a sede, distritos e povoados.

### Vias transitáveis (critério 360°)

Extensão, em km, das vias do **OpenStreetMap** que um veículo percorre, **recortadas no limite das manchas urbanas**. Só conta o trecho de cada via que está dentro da mancha.

**Entram** (tag `highway` do OSM): `motorway`, `trunk`, `primary`, `secondary`, `tertiary` e as respectivas alças `*_link`, `unclassified`, `residential`, `living_street`, `service`, `road` e `track` (ruas de terra).

**Ficam de fora**, mesmo dentro da mancha:
- vias com acesso privado ou proibido (`access=private/no`, `motor_vehicle=no`, `vehicle=no`)
- corredores de estacionamento, entradas de garagem e drive-thrus (`service=parking_aisle/driveway/drive-through`)
- calçadões, caminhos, escadas e ciclovias (não estão no filtro)

O comprimento é medido em SIRGAS 2000 / UTM 25S (EPSG:31985). Base OSM: 15/10/2026.

### Valor original do CONIAPE

O CONIAPE contava o **comprimento inteiro de toda via que toca a mancha urbana**, inclusive o trecho fora dela. Por isso as estradas que saem da cidade entravam inteiras, e o número original costuma ser **maior** que o transitável recortado. Exemplos: São Bento do Una 227 → 130 km; Bezerros 460 → 358 km.

O mapa e os relatórios gerados mostram os dois valores. Os **relatórios oficiais em PDF** continuam com o valor original.

### Casos especiais

- **Caruaru:** a extração original do CONIAPE estava **incompleta**: faltava a maior parte dos eixos do centro (1.016 km no original). Na nova extração, as manchas pequenas bateram exatamente com o original, o que valida o método. O valor atual é 1.501,18 km.
- **Ipojuca:** segue o plano específico do município, com três polígonos (Orla, O e Salgado, Sede e Ruropólis) em vez das manchas do IBGE, e o mesmo filtro de vias transitáveis.
- **Auditoria:** os 39 municípios foram comparados com o OSM atual pelo critério original. Só Caruaru tinha falha de extração (mais de 10% de diferença); veja `dados/auditoria_vias_osm_resumo.md`.

### Áreas do território

- **Território (área oficial IBGE):** área publicada pelo IBGE, que é a referência.
- **Território (planimétrica UTM 25S):** área calculada no plano da projeção. Difere pouco no Agreste; em municípios do Sertão, fora do fuso 25, a diferença chega a cerca de 2%.

---

## Parte 3: Baixar os dados

Todos os arquivos ficam na pasta [`dados/`](https://github.com/montieur/coniape-mapa-pe/tree/main/dados) do repositório:

| Arquivo | Conteúdo |
|---|---|
| [CONIAPE_PE_UTM25S_gpkg.zip](https://montieur.github.io/coniape-mapa-pe/dados/CONIAPE_PE_UTM25S_gpkg.zip) | GeoPackages: `PE_Municipios_CONIAPE_UTM25S.gpkg` e `CONIAPE_PE_UTM25S.gpkg` (camadas `vias_urbanas` e `areas_urbanas`) |
| [CONIAPE_PE_UTM25S_shp.zip](https://montieur.github.io/coniape-mapa-pe/dados/CONIAPE_PE_UTM25S_shp.zip) | Os mesmos dados em shapefile |
| [quantitativos_municipios.csv](https://montieur.github.io/coniape-mapa-pe/dados/quantitativos_municipios.csv) | Um município por linha (abre direto no Excel: `;` e vírgula decimal) |
| [quantitativos_manchas.csv](https://montieur.github.io/coniape-mapa-pe/dados/quantitativos_manchas.csv) | Uma mancha urbana por linha |
| [auditoria_vias_osm.csv](https://montieur.github.io/coniape-mapa-pe/dados/auditoria_vias_osm.csv) | Comparação CONIAPE × OSM por município |
| [revisoes.json](https://montieur.github.io/coniape-mapa-pe/dados/revisoes.json) | Registro técnico das revisões: valores, critério, km por tipo de via, excluídas, manchas |
| [Manual_CONIAPE_PE.pdf](https://montieur.github.io/coniape-mapa-pe/dados/Manual_CONIAPE_PE.pdf) | Este manual em PDF, com os prints |

Todas as camadas estão em **SIRGAS 2000 / UTM zona 25S (EPSG:31985)**.

### Campos: municípios (`PE_Municipios_CONIAPE_UTM25S`)

| Campo | Descrição |
|---|---|
| `CD_MUN`, `NM_MUN` | Código e nome IBGE do município |
| `NM_RGI`, `NM_RGINT` | Regiões geográficas imediata e intermediária (IBGE) |
| `CONIAPE` | `Sim` para os 40 municípios do CONIAPE |
| `AREA_IBGE` | Área territorial oficial IBGE (km²) |
| `AREA_UTM` | Área planimétrica em UTM 25S (km²) |
| `AREA_URB`, `AREA_RUR` | Área urbana e rural pelos setores IBGE 2022 (km²) |
| `VIAS_KM` | Vias transitáveis recortadas nas manchas (km) |
| `PERC_URB` | Área urbana / território (%) |
| `DENS_VIAS` | `VIAS_KM` / `AREA_URB` (km/km²) |
| `SETORES` | Número de setores censitários urbanos |
| `DISTRITOS` | Número de manchas urbanas |
| `FONTE` | Origem dos dados e data da revisão |

### Campos: vias (`vias_urbanas`) e áreas urbanas (`areas_urbanas`)

| Camada | Campos |
|---|---|
| `vias_urbanas` | `CD_MUN`, `NM_MUN`, `NOME_VIA` (nome da rua ou, sem nome, o tipo OSM), `COMP_KM` (trecho dentro da mancha, km) |
| `areas_urbanas` | `CD_MUN`, `NM_MUN`, `NOME` (mancha), `AREA_KM2` |

---

## Parte 4: Atualizar e publicar (manutenção)

### Requisitos

- **QGIS 3.44 LTR (OSGeo4W)**, com `C:\OSGeo4W\bin\python-qgis-ltr.bat` para os scripts PyQGIS
- **Python 3** (`C:\Python314\python.exe`) para os scripts sem QGIS
- **Git** e **GitHub CLI** (`gh`) logado na conta `montieur`
- Pastas de origem do CONIAPE em `Desktop\CONIAPE` (uma por município, com `quantitativos.json` e os KMLs)

### Estrutura de pastas

```
CONIAPE\MAPA_PE\
├─ 00_osm_download\   vias baixadas do OSM (GeoJSON por município)
├─ 01_dados\          intermediários: revisoes.json, auditoria, GeoJSON da web
├─ 02_shape_utm\      produtos finais em UTM 25S (.gpkg e shp\)
└─ 03_mapa_html\      ESTE repositório (site + dados\ + build\)
```

### Scripts (`build/`)

| Script | Para quê |
|---|---|
| `prep_coniape.py` | Lê os `quantitativos.json` do CONIAPE e gera CSV e listas de KML |
| `osm_vias_municipio.py <pasta> [transitavel]` | Baixa as vias do município no OSM (Overpass) |
| `vias_transitaveis_mancha.py` | Filtra as vias transitáveis e recorta nas manchas (PyQGIS) |
| `medir_vias_manchas.py` | Mede pelo critério antigo do CONIAPE (via inteira), para auditoria |
| `aplicar_revisao_vias.py` / `aplicar_revisao_lote.py` | Grava as vias novas nos produtos UTM e em `revisoes.json` |
| `build_data.py` | Gera o `data.js` do mapa e copia os PDFs oficiais |
| `compilar_pacote.py` | Gera os ZIPs e CSVs de `dados/` |
| `capturar_prints.py` | Tira os prints deste manual (`docs/img/`) e gera o PDF do manual, com o Edge headless |
| `gerar_icones.py` | Gera os ícones PNG do app a partir de `icones/icone.svg` |
| `auditoria/` | Scripts auxiliares da auditoria CONIAPE × OSM |

### Atualizar as vias de um município

Exemplo com Bezerros (`04_Bezerros`, código `2601904`). Rode na pasta `03_mapa_html\build`:

```bat
C:\Python314\python.exe -I osm_vias_municipio.py 04_Bezerros transitavel
C:\OSGeo4W\bin\python-qgis-ltr.bat vias_transitaveis_mancha.py ..\..\00_osm_download\04_Bezerros_osm_vias_transitavel.geojson 04_Bezerros 2601904 ..\..\01_dados\bezerros.gpkg ..\..\01_dados\bezerros.json
C:\OSGeo4W\bin\python-qgis-ltr.bat aplicar_revisao_vias.py 2601904 ..\..\01_dados\bezerros.gpkg ..\..\01_dados\bezerros.json
C:\Python314\python.exe -I build_data.py
C:\Python314\python.exe -I compilar_pacote.py
```

Para vários municípios de uma vez, ponha os pares `<pasta>_transitavel.gpkg` / `.json` numa pasta e rode `aplicar_revisao_lote.py <pasta>`.

Cuidados:
- **Faça backup de `02_shape_utm`** antes de aplicar uma revisão. O valor original do CONIAPE fica preservado em `revisoes.json` mesmo depois de várias revisões.
- O Overpass às vezes devolve erro 502/504 ou base desatualizada nos espelhos. Confira a data `base OSM` impressa no download.
- Feche no QGIS as camadas de `02_shape_utm` antes de aplicar, ou ao menos não as edite enquanto o script roda.

### Atualizar os prints e o PDF do manual

Depois de mudar o mapa ou este manual, com o site servido localmente:

```bat
C:\Python314\python.exe -m http.server 8791 --directory C:\Users\tecgeo-jordy\Desktop\CONIAPE\MAPA_PE\03_mapa_html
C:\Python314\python.exe -I build\capturar_prints.py http://localhost:8791
```

O script regrava os prints em `docs/img/` e o `dados/Manual_CONIAPE_PE.pdf`, gerado a partir de `manual.html`. Os prints de celular saem numa moldura de 390 × 844 px (`build/moldura_celular.html`).

### Publicar

Na pasta `03_mapa_html`:

```bat
git add -A
git commit -m "Atualiza vias de <município>"
git push
```

O GitHub Pages atualiza o site em 1 a 2 minutos. O `build_data.py` grava uma versão no endereço do `data.js` e do `relatorio.js` (`?v=<hash>`), para o navegador não reaproveitar dados antigos do cache.

### Configurações no código

- **`PDF_BASE_URL`** (`index.html`): onde ficam os relatórios oficiais. Vazio = pasta `relatorios/` do próprio site.
- **`PDF_TILES`** (`relatorio.js`): mapa base dos PDFs (Esri cinza claro + rótulos).

---

*TECGEO · Dados: IBGE (malha municipal 2024, setores censitários 2022), OpenStreetMap (© colaboradores OSM, ODbL), CONIAPE.*
