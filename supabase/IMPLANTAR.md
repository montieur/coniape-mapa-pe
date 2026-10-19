# Implantar o servidor do GIS Comercial

O servidor já está implantado no projeto **GIS-Comercial** (`cxvlkimvgmifjwwdaxgj`, conta JordyMonteiro's Org, plano gratuito,
região São Paulo). Este guia registra como foi feito, para refazer em outro projeto ou recuperar em caso de problema.

## Como funciona

```
visitante ──busca──► mapa ──pedido──► função gc-solicitar (Supabase)
                       ▲                  │ valida o município no IBGE, limita abuso, confere o IBGE na hora
                       │                  ▼
              lê o catálogo e os      tabela gc_pedidos (fila: gerar · atualizar · verificar)
              arquivos (público)          │
                       ▲                  ▼
                       │           GitHub Actions (processar-fila.yml, a cada 5 min)
              Storage gc-municipios ◄──── worker/processar_fila.py
              + tabela gc_municipios       · gerar/atualizar: setores do IBGE + vias do OpenStreetMap
                                           · verificar: o OSM mudou na área desde a extração?
```

- **Por que a automação confere o OpenStreetMap:** os servidores do Overpass recusam o ambiente das Edge Functions do Supabase
  (testado: 403, 406 e timeout), mas respondem às máquinas do GitHub. Por isso a função só confere o IBGE na hora e lê o
  resultado do OSM que a automação guarda; se estiver velho (mais de 24 h) ou ausente, enfileira um pedido `verificar`.
- **Quem pode pedir:** qualquer visitante, mas só por município que existe no IBGE. Geração/atualização: 5 por hora por visitante e
  150 por dia no total. Conferência: 40 por hora por visitante.
- **Leitura:** pública (o mapa é público). **Escrita:** só a função e a automação, com a chave de serviço, que nunca vai para o navegador.
- **Custos:** GitHub Actions é gratuito em repositório público; o projeto Supabase está no plano gratuito.

## O que foi feito (e como refazer)

Requisitos: Node (para `npx supabase`), `gh` logado na conta dona do repositório, e login do Supabase CLI na conta certa
(`npx supabase login`; confira com `npx supabase projects list`).

1. **Projeto:** `npx supabase projects create GIS-Comercial --org-id <org> --region sa-east-1 --db-password <senha aleatória>`
   (em organização do plano gratuito não se informa `--size`).
2. **Tabelas, bucket e regras de acesso** (rode na pasta do repositório; `--linked` é obrigatório junto do `--project-ref`):
   ```
   npx supabase db query --linked --project-ref <ref> -f supabase/migrations/20261019000000_gis_comercial.sql
   npx supabase db query --linked --project-ref <ref> -f supabase/migrations/20261019010000_pedido_verificar.sql
   ```
   Não use `supabase db push` num projeto que já tem outras migrações: ele compara com o histórico do projeto.
3. **Função:** `npx supabase functions deploy gc-solicitar --project-ref <ref> --use-api` (o `--use-api` dispensa o Docker).
   Segredo do IP dos visitantes: `npx supabase secrets set IP_SALT=<texto aleatório> --project-ref <ref>`.
4. **Chaves:** `npx supabase projects api-keys --project-ref <ref> -o json`. A **anon** (pública) vai em `config.js`
   (`supabaseUrl` e `anonKey`). A **service_role** (secreta) vai só para os segredos do repositório:
   `gh secret set SUPABASE_URL` e `gh secret set SUPABASE_SERVICE_KEY` (cole a chave quando o `gh` pedir; nunca em arquivo versionado).
5. **Semente dos 39 municípios do CONIAPE** (para eles também terem a conferência de atualização):
   com `SUPABASE_URL` e `SUPABASE_SERVICE_KEY` no ambiente, `python -X utf8 build/semear_base.py` (confere) e depois `--enviar`.
6. **Automação:** em `.github/workflows/processar-fila.yml` o agendamento (`schedule`/`cron`) fica ligado; dá para rodar na hora com
   `gh workflow run processar-fila.yml`.
7. **Mapa:** `python -I build/build_data.py` (versiona os scripts) e `git push`.

*Opcional, para gerar na hora em vez de esperar até 5 minutos:* crie um token do GitHub (fine-grained) com permissão **Actions:
Read and write** só neste repositório e rode `npx supabase secrets set GITHUB_DISPATCH_TOKEN=<token> --project-ref <ref>`.
Não use o token do `gh` (tem acesso amplo à conta).

## Conferir que funciona

- Abra o mapa, digite um município que não está na base (ex.: Gravatá) e clique em **Gerar dados**. Em alguns minutos ele entra
  na base, com origem **Pesquisa**.
- Abra um município do CONIAPE: o cartão **Fontes de dados** mostra "Conferindo no OpenStreetMap…" e, depois, o resultado.
- No GitHub, aba **Actions**, "Processar fila do GIS Comercial" mostra o passo a passo de cada geração.
- Teste de ponta a ponta sem Supabase: `python -X utf8 worker/teste_fila_local.py <código IBGE>` (usa um servidor falso).

## Limites e cuidados

- **Overpass (OpenStreetMap):** os servidores públicos oscilam e têm limite de uso. O gerador tenta cinco servidores em rodízio;
  uma geração pode falhar, volta à fila até 3 vezes e depois mostra o erro. Para uso comercial intenso, considere um Overpass próprio.
- **Municípios muito grandes** (capitais) geram muitas consultas e podem passar de 10 minutos.
- **GitHub desliga agendamentos** de repositórios sem nenhuma atividade por 60 dias; um `git push` reativa.
- **Dados do IBGE:** setores censitários de 2022 por estado (de 6 MB a 180 MB); o GitHub guarda em cache os já usados.
- **Atribuição:** dados do OpenStreetMap exigem "© colaboradores do OpenStreetMap" (já está no manual e no mapa).
- **Senha do banco:** foi gerada na criação do projeto e não foi guardada. Se precisar de acesso direto ao Postgres, redefina em
  Supabase > Project Settings > Database.
