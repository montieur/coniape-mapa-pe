/* GIS Comercial · configuração do servidor de municípios.
   Sem estes valores o mapa funciona só com os municípios que já vêm no site (busca e geração ficam desativadas).
   A chave "anon" do Supabase é pública por desenho: só consegue LER as tabelas e chamar a função gc-solicitar.
   Os segredos de escrita (service_role) ficam nos segredos do GitHub e do Supabase, nunca aqui. */
window.GC_CONFIG = {
  supabaseUrl: '',   // ex.: 'https://abcdefghijkl.supabase.co'
  anonKey: '',       // chave pública (anon) do projeto
  bucket: 'gc-municipios',
};
