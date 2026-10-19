-- GIS Comercial · municípios gerados sob demanda
--
-- Modelo:
--   gc_municipios  um registro por município pronto (resumo + procedência das fontes + arquivo no Storage)
--   gc_pedidos     fila de geração/atualização; a automação (GitHub Actions) processa e grava o resultado
--   storage        bucket público "gc-municipios": <código IBGE>.json com as geometrias e as vias
--
-- Segurança: leitura pública (o mapa é público). Escrita só pelo servidor (função gc-solicitar e a automação,
-- ambas com a chave de serviço); o visitante nunca grava direto nas tabelas.
-- As tabelas usam o prefixo gc_ e ficam no schema public, para conviverem com outros sistemas do mesmo projeto.

create table if not exists public.gc_municipios (
  cd_mun        text primary key check (cd_mun ~ '^[0-9]{7}$'),
  nome          text not null,
  uf            text not null,
  rgi           text,
  rgint         text,
  origem        text not null default 'pesquisa' check (origem in ('coniape', 'pesquisa')),
  resumo        jsonb not null,                 -- {aI, aU, urb, rur, vias, perc, dens, set, dist}
  contorno      jsonb,                          -- limite municipal simplificado (GeoJSON), para o mapa listar sem baixar o arquivo pesado
  fontes        jsonb not null,                 -- {ibge_setores:{url,last_modified,content_length}, osm:{base,bbox,...}, criterio}
  arquivo       text not null,                  -- caminho no bucket gc-municipios
  versao        int  not null default 1,
  gerado_em     timestamptz not null default now(),
  verificado_em timestamptz,                    -- última checagem de atualização das fontes
  verificacao   jsonb,                          -- resultado dessa checagem
  atualizado_em timestamptz not null default now()
);

create table if not exists public.gc_pedidos (
  id           uuid primary key default gen_random_uuid(),
  cd_mun       text not null check (cd_mun ~ '^[0-9]{7}$'),
  tipo         text not null default 'gerar' check (tipo in ('gerar', 'atualizar')),
  status       text not null default 'fila' check (status in ('fila', 'processando', 'pronto', 'erro')),
  mensagem     text,
  tentativas   int  not null default 0,
  ip_hash      text,                            -- só para limitar abuso; nunca exposto ao público
  criado_em    timestamptz not null default now(),
  iniciado_em  timestamptz,
  concluido_em timestamptz
);

-- no máximo um pedido ativo por município (evita fila duplicada)
create unique index if not exists gc_pedidos_um_ativo on public.gc_pedidos (cd_mun) where status in ('fila', 'processando');
create index if not exists gc_pedidos_fila on public.gc_pedidos (status, criado_em);
create index if not exists gc_pedidos_ip on public.gc_pedidos (ip_hash, criado_em);

alter table public.gc_municipios enable row level security;
alter table public.gc_pedidos    enable row level security;

drop policy if exists gc_municipios_leitura on public.gc_municipios;
create policy gc_municipios_leitura on public.gc_municipios for select to anon, authenticated using (true);
drop policy if exists gc_pedidos_leitura on public.gc_pedidos;
create policy gc_pedidos_leitura on public.gc_pedidos for select to anon, authenticated using (true);

-- o público só enxerga as colunas que interessam (sem ip_hash) e não escreve em nada
revoke all on public.gc_municipios from anon, authenticated;
revoke all on public.gc_pedidos    from anon, authenticated;
grant select on public.gc_municipios to anon, authenticated;
grant select (id, cd_mun, tipo, status, mensagem, criado_em, iniciado_em, concluido_em) on public.gc_pedidos to anon, authenticated;

-- bucket público de leitura; só a chave de serviço escreve
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('gc-municipios', 'gc-municipios', true, 52428800, array['application/json'])
on conflict (id) do update set public = excluded.public, file_size_limit = excluded.file_size_limit,
                               allowed_mime_types = excluded.allowed_mime_types;

comment on table public.gc_municipios is 'GIS Comercial: municípios com dados gerados (resumo, fontes, arquivo no Storage)';
comment on table public.gc_pedidos    is 'GIS Comercial: fila de geração e atualização de municípios';
