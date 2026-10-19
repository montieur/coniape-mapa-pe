-- Novo tipo de pedido: "verificar" (conferir se o OpenStreetMap mudou na área de um município).
-- A conferência roda na automação do GitHub, porque os servidores do Overpass recusam o ambiente do Supabase
-- (testado: 403/406/timeout a partir das Edge Functions), mas respondem às máquinas do GitHub.
alter table public.gc_pedidos drop constraint if exists gc_pedidos_tipo_check;
alter table public.gc_pedidos add constraint gc_pedidos_tipo_check check (tipo in ('gerar', 'atualizar', 'verificar'));
