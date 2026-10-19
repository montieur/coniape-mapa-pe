/* GIS Comercial · configuração do servidor de municípios.
   Sem estes valores o mapa funciona só com os municípios que já vêm no site (busca e geração ficam desativadas).
   A chave "anon" do Supabase é pública por desenho: só consegue LER as tabelas e chamar a função gc-solicitar.
   Os segredos de escrita (service_role) ficam nos segredos do GitHub e do Supabase, nunca aqui. */
window.GC_CONFIG = {
  supabaseUrl: 'https://cxvlkimvgmifjwwdaxgj.supabase.co',   // ex.: 'https://abcdefghijkl.supabase.co'
  anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN4dmxraW12Z21pZmp3d2RheGdqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTI0Mzk3NDMsImV4cCI6MjEwODAxNTc0M30.zyYckrlsDu8CtUAOilSS85kxN0tSPp253F1fB_ZzWP4',       // chave pública (anon) do projeto
  bucket: 'gc-municipios',
};
