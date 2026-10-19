# Implantar o servidor do GIS Comercial

O mapa já está pronto para gerar municípios sob demanda; falta ligar o servidor. Enquanto `config.js` estiver vazio, o mapa
funciona como antes (só os municípios que já vêm no site).

## Como funciona

```
visitante ──busca──► mapa ──pedido──► função gc-solicitar (Supabase)
                       ▲                  │ valida o município no IBGE, limita abuso
                       │                  ▼
              lê o catálogo e os      tabela gc_pedidos (fila)
              arquivos (público)          │
                       ▲                  ▼
                       │           GitHub Actions (processar-fila.yml)
              Storage gc-municipios ◄──── worker/processar_fila.py gera o município
              + tabela gc_municipios       (IBGE: setores · OpenStreetMap: vias) e grava o resultado
```

- **Quem pode pedir:** qualquer visitante, mas só por município que existe no IBGE, no máximo 5 pedidos por hora por visitante e 150 por dia no total.
- **Leitura:** pública (o mapa é público). **Escrita:** só a função e a automação, com a chave de serviço, que nunca vai para o navegador.
- **Custos:** o GitHub Actions é gratuito em repositório público. O Supabase cobra pelo projeto conforme o plano da organização.

## Passo a passo

1. **Escolha o projeto Supabase.** Recomendado: um projeto novo só para isto (ex.: `GIS-Comercial`), porque o mapa é público.
   Dá para usar um projeto existente: as tabelas têm prefixo `gc_`. Anote o **Project ref** (a parte `xxxx` de `https://xxxx.supabase.co`).
2. **Instale e entre no CLI:** `npm i -g supabase` e `supabase login`.
3. **Crie as tabelas, o bucket e as regras de acesso:**
   `supabase link --project-ref <ref>` e depois `supabase db push` (usa `supabase/migrations/20261019000000_gis_comercial.sql`).
   Sem o CLI, cole o conteúdo desse arquivo no SQL Editor do Supabase e execute.
4. **Publique a função:** `supabase functions deploy gc-solicitar`.
   Segredo para embaralhar o IP dos visitantes: `supabase secrets set IP_SALT=<texto longo e aleatório>`.
   *Opcional* (gera na hora em vez de esperar até 5 min): crie um token do GitHub com permissão **Actions: Read and write**
   só neste repositório e rode `supabase secrets set GITHUB_DISPATCH_TOKEN=<token>`.
5. **Segredos da automação no GitHub** (Settings > Secrets and variables > Actions, ou pelo `gh`):
   `gh secret set SUPABASE_URL --body "https://<ref>.supabase.co"` e `gh secret set SUPABASE_SERVICE_KEY` (cola a chave **service_role**).
6. **Semeie os 39 municípios do CONIAPE** (para eles também terem a conferência de atualização):
   `SUPABASE_URL` e `SUPABASE_SERVICE_KEY` no ambiente, depois
   `python -X utf8 build/semear_base.py` (confere) e `python -X utf8 build/semear_base.py --enviar`.
7. **Ligue a automação:** em `.github/workflows/processar-fila.yml`, descomente as linhas `schedule` e `cron`.
8. **Ligue o mapa:** preencha `supabaseUrl` e `anonKey` (chave **anon**, pública) em `config.js`, rode `python -I build/build_data.py` e publique (`git push`).

## Conferir se funcionou

- Abra o mapa, digite um município que não está na base (ex.: Pesqueira) e clique em **Gerar dados**.
- Em até uns 5 minutos o município aparece na base, com origem **Pesquisa**.
- Abra um município do CONIAPE: o cartão **Fontes de dados** diz se há atualização.
- No GitHub, aba **Actions**, o fluxo "Processar fila do GIS Comercial" mostra o passo a passo de cada geração.

## Limites e cuidados

- **Overpass (OpenStreetMap):** os servidores públicos oscilam e têm limite de uso. O gerador tenta cinco servidores em rodízio, mas
  uma geração pode falhar; ela volta à fila até 3 vezes e depois mostra o erro. Para uso comercial intenso, considere um Overpass próprio.
- **Municípios muito grandes** (capitais) geram muitas consultas e podem passar de 10 minutos.
- **GitHub desliga agendamentos** de repositórios sem nenhuma atividade por 60 dias; um `git push` reativa.
- **Dados do IBGE:** setores censitários de 2022 por estado (de 6 MB a 180 MB). O GitHub guarda em cache os já usados.
- **Atribuição:** dados do OpenStreetMap exigem a menção "© colaboradores do OpenStreetMap" (já está no manual e no rodapé do mapa).
