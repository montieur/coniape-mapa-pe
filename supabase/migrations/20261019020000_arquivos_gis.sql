-- Arquivos GIS para baixar (SHP, KML, KMZ) de cada município: limite, área urbana/rural, vias urbanas/rurais.
-- Ficam no bucket gc-municipios, em arquivos/<código IBGE>/…; o caminho de cada um fica em gc_municipios.arquivos.
alter table public.gc_municipios add column if not exists arquivos jsonb;   -- {shp, kml, kmz, camadas, gerado_em}

alter table public.gc_pedidos drop constraint if exists gc_pedidos_tipo_check;
alter table public.gc_pedidos add constraint gc_pedidos_tipo_check
  check (tipo in ('gerar', 'atualizar', 'verificar', 'exportar'));

-- o bucket passa a aceitar também os arquivos GIS (a escrita continua só pela chave de serviço)
update storage.buckets
   set allowed_mime_types = array['application/json', 'application/zip',
                                  'application/vnd.google-earth.kml+xml', 'application/vnd.google-earth.kmz'],
       file_size_limit = 52428800
 where id = 'gc-municipios';

-- leitura pública do novo campo (o público já lê o catálogo inteiro; a tabela segue sem escrita para ele)
grant select on public.gc_municipios to anon, authenticated;
