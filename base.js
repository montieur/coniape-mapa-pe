/* GIS Comercial · base compartilhada
   - busca de qualquer município do Brasil (autocompletar sobre a lista do IBGE)
   - município fora da base: pede a geração ao servidor e acompanha o andamento
   - município que já existe: confere se as fontes (IBGE e OpenStreetMap) mudaram e avisa
   - tudo que é gerado fica guardado no servidor e passa a aparecer para todos
   Usa os globais do index.html (D, CO, byCode, map, munLayer, urbLayer, select, renderDetail…). */
(() => {
  'use strict';
  const CFG = window.GC_CONFIG || {};
  const PARAMS = new URLSearchParams(location.search);
  const MOCK = PARAMS.has('mock');                       // só para testar a tela sem servidor (dados/_mock/<cód>.json)
  const SERVIDOR = !!(CFG.supabaseUrl && CFG.anonKey) || MOCK;
  const BUCKET = CFG.bucket || 'gc-municipios';
  const el = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  // data pura (aaaa-mm-dd) é dia local; só datas com hora entram no fuso (senão 15/10 vira 14/10 em Recife)
  const dataBr = iso => !iso ? '?' : /^\d{4}-\d{2}-\d{2}$/.test(iso) ? iso.split('-').reverse().join('/') : new Date(iso).toLocaleDateString('pt-BR');
  const horaBr = iso => iso ? new Date(iso).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'}) : '';
  const guardar = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, JSON.stringify(v)); } catch { /* sem armazenamento local */ } };
  const ler = k => { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } };
  const zonaDe = epsg => epsg ? Number(String(epsg).replace('EPSG:', '')) - 31960 : 25;

  /* ================= servidor (Supabase) ================= */
  const hdr = () => ({apikey: CFG.anonKey, Authorization: 'Bearer ' + CFG.anonKey});
  async function rest(caminho) {
    const r = await fetch(`${CFG.supabaseUrl}/rest/v1/${caminho}`, {headers: hdr()});
    if (!r.ok) throw new Error('Servidor respondeu ' + r.status);
    return r.json();
  }
  const api = {
    catalogo: cd => rest('gc_municipios?select=cd_mun,nome,uf,rgi,rgint,origem,resumo,contorno,fontes,gerado_em,verificado_em,verificacao,arquivos'
      + (cd ? `&cd_mun=eq.${cd}` : '') + '&order=nome'),
    async pacote(cd, versao) {
      const r = await fetch(`${CFG.supabaseUrl}/storage/v1/object/public/${BUCKET}/${cd}.json?v=${encodeURIComponent(versao || '')}`);
      if (!r.ok) throw new Error('Arquivo do município indisponível (' + r.status + ')');
      return r.json();
    },
    async solicitar(cd, acao = 'consultar', forcar = false) {
      const r = await fetch(`${CFG.supabaseUrl}/functions/v1/gc-solicitar`, {
        method: 'POST', headers: {...hdr(), 'Content-Type': 'application/json'}, body: JSON.stringify({cd, acao, forcar})});
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.erro || 'Servidor respondeu ' + r.status);
      return j;
    },
    async pedido(id) { return (await rest(`gc_pedidos?id=eq.${id}&select=id,cd_mun,tipo,status,mensagem,criado_em,concluido_em`))[0]; },
  };
  if (MOCK) Object.assign(api, simulacao());

  /* simulação local para testar a tela: ?mock (município novo: fila 4 s, processando 5 s, pronto) · ?mock=mudou (há atualização) */
  function simulacao() {
    const t0 = {};
    const verif = mudou => ({verificado_em: new Date().toISOString(), mudou,
      ibge: {mudou: false}, osm: {mudou, vias_alteradas: mudou ? 37 : 0},
      resumo: mudou ? 'Há atualização desde 15/10/2026: 37 via(s) mudaram no OpenStreetMap na área.'
        : 'Sem atualização nas fontes desde 15/10/2026. Os dados já estão atualizados.'});
    const pacote = async cd => { const r = await fetch(`dados/_mock/${cd}.json`); if (!r.ok) throw new Error('sem arquivo de teste'); return r.json(); };
    return {
      // com código: a linha que o banco devolveria para um município gerado (montada a partir do arquivo de teste)
      catalogo: async cd => {
        if (!cd) return [];
        const p = await pacote(cd), m = p.mun;
        return [{cd_mun: cd, nome: m.n, uf: m.uf, rgi: m.rgi, rgint: m.rgint, origem: 'pesquisa', contorno: m.g, gerado_em: p.gerado_em, fontes: p.fontes,
          resumo: Object.fromEntries(['aI', 'aU', 'urb', 'rur', 'vias', 'perc', 'dens', 'set', 'dist'].map(k => [k, m[k]]))}];
      },
      pacote,
      solicitar: async (cd, acao) => {
        await new Promise(r => setTimeout(r, 700));
        const mudou = PARAMS.get('mock') === 'mudou';
        if (byCode[cd]?.co) {
          if (acao === 'atualizar' && mudou) { t0[cd] = Date.now(); return {existe: true, estado: 'fila', verificacao: verif(true), pedido: {id: 'mock-' + cd, status: 'fila'}, mensagem: 'Atualização registrada.'}; }
          return {existe: true, estado: 'pronto', verificacao: verif(mudou), mensagem: verif(mudou).resumo};
        }
        t0[cd] = Date.now();
        return {existe: false, estado: 'fila', pedido: {id: 'mock-' + cd, status: 'fila'}, mensagem: 'Pedido registrado. Os dados serão gerados em alguns minutos.'};
      },
      pedido: async id => {
        const cd = id.slice(5), s = (Date.now() - (t0[cd] ?? Date.now())) / 1000;
        return {id, cd_mun: cd, status: s < 4 ? 'fila' : s < 9 ? 'processando' : 'pronto'};
      },
    };
  }

  /* ================= lista de municípios do IBGE ================= */
  let listaIbge = null;
  const carregarLista = () => listaIbge ??= fetch('dados/municipios_ibge.json').then(r => r.json())
    .then(l => l.map(([cd, nome, uf]) => ({cd, nome, uf, s: slug(nome.toLowerCase())})));

  /* ================= incluir municípios na base ================= */
  function montar(r) {
    const s = r.resumo || {};
    return {c: r.cd_mun, n: r.nome, uf: r.uf, rgi: r.rgi, rgint: r.rgint, co: true, origem: r.origem, pdf: null,
      aI: s.aI, aU: s.aU, urb: s.urb, rur: s.rur, vias: s.vias, perc: s.perc, dens: s.dens, set: s.set, dist: s.dist,
      fonte: 'IBGE setores 2022 + vias OSM transitáveis (GIS Comercial)', g: r.contorno,
      fontes: r.fontes, gerado_em: r.gerado_em, verificado_em: r.verificado_em, verificacao: r.verificacao, arquivos: r.arquivos || null, detalhe: false};
  }
  function rotulo(m) {
    window.tirarRotuloCinza?.(m.c);
    labels.addLayer(L.tooltip({permanent: true, direction: 'center', className: 'mlabel', interactive: false})
      .setLatLng(layerByCode[m.c].getCenter()).setContent(m.n));
  }
  /* malha municipal de cada estado que tem município na base: os outros municípios do estado aparecem em cinza,
     com nome, prontos para serem pesquisados (PE já vem no site) */
  const ufsComMalha = new Set(['PE']);
  async function carregarMalhaUf(uf) {
    if (!uf || ufsComMalha.has(uf)) return;
    ufsComMalha.add(uf);
    try {
      const [lista, r] = await Promise.all([carregarLista(),
        fetch(`https://servicodados.ibge.gov.br/api/v3/malhas/estados/${uf}?formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=municipio`)]);
      if (!r.ok) throw new Error('IBGE ' + r.status);
      const nomes = Object.fromEntries(lista.map(x => [x.cd, x.nome]));
      (await r.json()).features.forEach(f => {
        const cd = String(f.properties.codarea);
        if (!byCode[cd]) window.adicionarMunCinza({c: cd, n: nomes[cd] || cd, uf, co: false, g: f.geometry});
      });
      munLayer.setStyle(styleMun);
      if (selected) layerByCode[selected]?.bringToFront();
    } catch (e) { ufsComMalha.delete(uf); console.warn('Malha do estado indisponível:', uf, e.message); }
  }

  function incluirNaBase(m, lote) {
    let alvo = byCode[m.c];
    if (!alvo) {                                            // fora do mapa de PE: entra com o contorno do catálogo
      if (!m.g) return null;
      D.mun.push(m); byCode[m.c] = alvo = m;
      munLayer.addData({type: 'Feature', properties: {c: m.c}, geometry: m.g});
      layerByCode[m.c] = munLayer.getLayers().at(-1);
    } else if (!alvo.co) {                                  // município de PE que estava em cinza: ganha dados
      Object.assign(alvo, m, {g: alvo.g || m.g});
    } else {                                                // já era da base (os do CONIAPE): só anota a procedência
      alvo.gerado_em ??= m.gerado_em; alvo.verificado_em ??= m.verificado_em; alvo.verificacao ??= m.verificacao; alvo.fontes ??= m.fontes; alvo.arquivos = m.arquivos || alvo.arquivos || null;
      return alvo;
    }
    if (!CO.includes(alvo)) CO.push(alvo);
    munBounds[alvo.c] = layerByCode[alvo.c].getBounds();
    rotulo(alvo);
    if (!lote) { reconstruir(); carregarMalhaUf(alvo.uf); }
    return alvo;
  }
  function reconstruir() { calcularRanks(); atualizarKpis(); setMetric(metric); }

  /* detalhe pesado (manchas e vias) só é baixado quando o município é aberto */
  const emCurso = {};
  function aplicarPacote(cd, p) {
    const m = byCode[cd], n = p.mun;
    for (const k of ['aI', 'aU', 'urb', 'rur', 'vias', 'perc', 'dens', 'set', 'dist']) m[k] = n[k];
    Object.assign(m, {excl: p.excluidas_km, por_tipo: p.por_tipo_km, zona: zonaDe(p.crs_medicao), areaRur: n.areaRur, viasRur: n.viasRur, gerado_em: p.gerado_em, fontes: p.fontes, detalhe: true});
    urbLayer.getLayers().filter(l => l.feature.properties.c === cd).forEach(l => urbLayer.removeLayer(l));
    D.urb = D.urb.filter(u => u.c !== cd).concat(p.urb);
    p.urb.forEach(u => urbLayer.addData({type: 'Feature', properties: u, geometry: u.g}));
    D.vias[cd] = p.vias;
    if (viaCache[cd]) { viasGroup.removeLayer(viaCache[cd]); delete viaCache[cd]; }
    D.distritos = D.distritos.filter(d => d.CD_MUN !== cd).concat(p.distritos);
    reconstruir(); refreshVias();
    if (selected === cd) renderDetail(m);
  }
  const carregarDetalhe = cd => byCode[cd].detalhe ? Promise.resolve(byCode[cd])
    : (emCurso[cd] ??= api.pacote(cd, byCode[cd].gerado_em).then(p => { aplicarPacote(cd, p); return byCode[cd]; }).finally(() => delete emCurso[cd]));
  window.garantirDetalhe = cd => carregarDetalhe(cd);   // o relatório de vários municípios usa para baixar vias e manchas

  /* ================= abrir município ================= */
  window.abrirMunicipio = async (cd, zoom = true) => {
    const m = byCode[cd];
    if (!m?.co) return window.abrirPesquisa(cd);
    document.querySelector('aside').classList.remove('pesquisa'); limparContorno(); clearInterval(relogio);
    if (!m.detalhe) {
      toast('Carregando os dados do município…', 0);
      try { await carregarDetalhe(cd); } catch (e) { toast('Não consegui carregar os dados deste município.'); return; }
      el('toast').classList.remove('on');
    }
    select(cd, zoom);
    consultarFontes(cd);
  };
  CO.forEach(m => { m.detalhe = true; m.origem ??= 'coniape'; });   // os que vieram no site já têm tudo

  /* ================= cartão "Fontes de dados" ================= */
  const redesenhar = cd => { if (selected === cd) renderDetail(byCode[cd]); };
  async function consultarFontes(cd, acao = 'consultar') {
    const m = byCode[cd];
    if (!SERVIDOR || !m?.co) return;
    if (acao === 'consultar' && m.verif?.estado === 'ok') return;       // já sabe
    m.verif = {estado: 'verificando'}; redesenhar(cd);
    try { aplicarResposta(cd, await api.solicitar(cd, acao)); }
    catch (e) { m.verif = {estado: 'erro', mensagem: e.message}; }
    redesenhar(cd);
  }
  /* resposta do servidor sobre um município da base: resultado da conferência ou pedido em andamento
     ('verificar' = conferindo o OpenStreetMap; 'atualizar' = gerando de novo) */
  function aplicarResposta(cd, r) {
    const ativo = r.pedido && ['fila', 'processando'].includes(r.estado);
    const tipo = r.pedido?.tipo || 'atualizar';
    const m = byCode[cd];
    if (r.municipio && 'arquivos' in r.municipio) m.arquivos = r.municipio.arquivos;
    if (tipo === 'exportar') {                           // preparar arquivos não impede a conferência das fontes
      m.arq = ativo ? {estado: 'preparando'} : null;
      m.verif = {estado: 'ok', verificacao: r.verificacao, mensagem: r.mensagem};
      if (ativo) acompanhar(cd, r.pedido.id, tipo);
      return;
    }
    if (!ativo && m.arq?.estado === 'preparando') m.arq = null;
    byCode[cd].verif = {estado: ativo ? (tipo === 'verificar' ? 'conferindo' : 'andamento') : 'ok', verificacao: r.verificacao, mensagem: r.mensagem};
    if (ativo) acompanhar(cd, r.pedido.id, tipo);
  }
  /* ================= cartão "Baixar dados GIS" (SHP, KML, KMZ) ================= */
  const tamanho = b => b >= 1e6 ? (b / 1e6).toFixed(1).replace('.', ',') + ' MB' : Math.max(1, Math.round(b / 1e3)) + ' KB';
  const NOMES_CAMADAS = {limite_municipal: 'Limite do município', area_urbana: 'Área urbana', area_rural: 'Área rural', vias_urbanas: 'Vias urbanas', vias_rurais: 'Vias rurais'};
  function cartaoArquivos(m) {
    const a = m.arquivos;
    let corpo, acoes = '', cls = 'neutro';
    if (m.arq?.estado === 'preparando') { cls = 'carregando'; corpo = '<i class="spin"></i><span>Preparando os arquivos GIS. Leva alguns minutos; pode continuar usando o mapa.</span>'; }
    else if (!a) {
      corpo = `<span>Limite, área urbana, área rural e vias (urbanas e rurais) em Shapefile, KML e KMZ.${m.arq?.estado === 'erro' ? ` <b>Não deu certo:</b> ${esc(m.arq.mensagem)}` : ''}</span>`;
      acoes = `<button class="btn primary" data-arq="preparar">Preparar arquivos GIS</button>`;
    } else {
      const d = a.drive;                                   // novos: Google Drive · antigos: Storage do Supabase
      const url = c => d ? `https://drive.google.com/uc?export=download&id=${d[c]}`
        : `${CFG.supabaseUrl}/storage/v1/object/public/${BUCKET}/${a[c]}?download=${encodeURIComponent(a[c].split('/').pop())}`;
      const t = a.tamanhos || {};
      cls = 'ok';
      corpo = `<span>${Object.entries(a.camadas || {}).map(([k, v]) => `${NOMES_CAMADAS[k] || k}: ${v.km2 != null ? fmt(v.km2) + ' km²' : fmt(v.km) + ' km'}`).join(' · ')}</span>`;
      acoes = `<a class="btn primary" href="${url('shp')}" download>Shapefile (.zip)${t.shp ? ` · ${tamanho(t.shp)}` : ''}</a>`
        + `<a class="btn" href="${url('kmz')}" download>KMZ${t.kmz ? ` · ${tamanho(t.kmz)}` : ''}</a>`
        + (d ? `<a class="btn" href="${url('kml')}" download>KML${t.kml ? ` · ${tamanho(t.kml)}` : ''}</a>${d.pdf ? `<a class="btn" href="${url('pdf')}" download>Relatório PDF</a>` : ''}<a class="btn" href="https://drive.google.com/drive/folders/${d.pasta}" target="_blank" rel="noopener">Abrir no Drive</a>`
          : `<button class="btn" data-arq="kml" data-kmz="${url('kmz')}" data-nome="${esc(a.kmz.split('/').pop().replace(/\.kmz$/, '.kml'))}">KML</button>`);
    }
    return `<div class="fontes arquivos ${cls}" data-cd="${m.c}">
      <div class="fh"><b>Baixar dados GIS</b><small>SHP em UTM · KML/KMZ em WGS 84</small></div>
      <div class="fv">${corpo}</div>
      ${acoes ? `<div class="fa">${acoes}</div>` : ''}
      ${a ? '<div class="fl">Vias © colaboradores do OpenStreetMap (ODbL); limites e áreas: IBGE.</div>' : ''}</div>`;
  }
  /* o KML é o doc.kml de dentro do KMZ: extraído aqui, sem guardar um segundo arquivo (3 a 4 vezes maior) no servidor */
  let jszip = null;
  const carregarJsZip = () => jszip ??= new Promise((ok, falha) => {
    const sc = Object.assign(document.createElement('script'), {src: 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js', onload: ok, onerror: () => falha(new Error('JSZip'))});
    document.head.appendChild(sc);
  });
  async function baixarKml(b) {
    const rotulo = b.textContent; b.disabled = true; b.textContent = 'Preparando KML…';
    try {
      await carregarJsZip();
      const r = await fetch(b.dataset.kmz); if (!r.ok) throw new Error('HTTP ' + r.status);
      const z = await JSZip.loadAsync(await r.arrayBuffer());
      const kml = await z.file('doc.kml').async('blob');
      const a = Object.assign(document.createElement('a'), {href: URL.createObjectURL(new Blob([kml], {type: 'application/vnd.google-earth.kml+xml'})), download: b.dataset.nome});
      document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    } catch (e) { toast('Não consegui preparar o KML: ' + e.message + '. Use o KMZ, que abre no Google Earth.', 6000); }
    b.disabled = false; b.textContent = rotulo;
  }
  async function prepararArquivos(cd) {
    const m = byCode[cd]; m.arq = {estado: 'preparando'}; redesenhar(cd);
    try { aplicarResposta(cd, await api.solicitar(cd, 'exportar'));
      if (m.arq?.estado === 'preparando' && !pendentes()[cd]) m.arq = null; }
    catch (err) { m.arq = {estado: 'erro', mensagem: err.message}; }
    redesenhar(cd);
  }
  window.cartaoFontes = m => {
    if (!SERVIDOR) return '';                    // sem servidor ativo o detalhe fica como era
    return cartaoFontesBase(m) + cartaoArquivos(m);
  };
  const cartaoFontesBase = m => {
    const gerado = m.gerado_em || m.rev?.data;
    const f = m.fontes;
    const linhaFontes = `IBGE: setores censitários 2022${f?.ibge_setores?.last_modified ? ` (arquivo de ${dataBr(f.ibge_setores.last_modified)})` : ''} · `
      + `OpenStreetMap${f?.osm?.base ? ` (de ${dataBr(f.osm.base)})` : ''}`;
    const v = m.verif;
    let corpo = '', cls = 'neutro', acoes = '';
    if (!SERVIDOR) corpo = 'A conferência automática de atualização fica disponível quando o servidor do GIS Comercial estiver ativo.';
    else if (!v || v.estado === 'verificando') { cls = 'carregando'; corpo = 'Conferindo se as fontes mudaram…'; }
    else if (v.estado === 'erro') { cls = 'aviso'; corpo = `Não consegui conferir agora: ${esc(v.mensagem)}`; acoes = `<button class="btn" data-fonte="verificar">Tentar de novo</button>`; }
    else if (v.estado === 'conferindo') { cls = 'carregando'; corpo = `${esc(v.verificacao?.resumo || 'Conferindo no OpenStreetMap…')} <small>Pode levar alguns minutos; pode continuar usando o mapa.</small>`; }
    else if (v.estado === 'andamento') { cls = 'carregando'; corpo = 'Atualização em andamento. Pode continuar usando o mapa: os dados novos entram sozinhos quando ficarem prontos.'; }
    else {
      const vv = v.verificacao;
      if (vv?.mudou === false) { cls = 'ok'; corpo = esc(vv.resumo); acoes = `<button class="btn" data-fonte="verificar">Verificar de novo</button>`; }
      else if (vv?.mudou === true) { cls = 'novo'; corpo = esc(vv.resumo); acoes = `<button class="btn primary" data-fonte="atualizar">Atualizar dados</button><button class="btn" data-fonte="verificar">Verificar de novo</button>`; }
      else { cls = 'aviso'; corpo = esc(vv?.resumo || v.mensagem || 'Não foi possível confirmar se há atualização.'); acoes = `<button class="btn" data-fonte="verificar">Tentar de novo</button>`; }
      if (vv?.verificado_em) corpo += ` <small>Conferido em ${dataBr(vv.verificado_em)} às ${horaBr(vv.verificado_em)}.</small>`;
    }
    return `<div class="fontes ${cls}" data-cd="${m.c}">
      <div class="fh"><b>Fontes de dados</b>${gerado ? `<small>gerado em ${dataBr(gerado)}</small>` : ''}</div>
      <div class="fl">${linhaFontes}</div>
      <div class="fv">${cls === 'carregando' ? '<i class="spin"></i>' : ''}<span>${corpo}</span></div>
      ${acoes ? `<div class="fa">${acoes}</div>` : ''}</div>`;
  };
  el('detail').addEventListener('click', async e => {
    const ba = e.target.closest('[data-arq]');
    if (ba?.dataset.arq === 'kml') { baixarKml(ba); return; }
    if (ba) { prepararArquivos(ba.closest('.arquivos').dataset.cd); return; }
    const b = e.target.closest('[data-fonte]'); if (!b) return;
    const cd = b.closest('.fontes').dataset.cd;
    if (b.dataset.fonte === 'verificar') consultarFontes(cd, 'verificar');
    else if (b.dataset.fonte === 'atualizar') {
      const m = byCode[cd]; m.verif = {estado: 'verificando'}; redesenhar(cd);
      try { aplicarResposta(cd, await api.solicitar(cd, 'atualizar')); }
      catch (err) { m.verif = {estado: 'erro', mensagem: err.message}; }
      redesenhar(cd);
    }
  });

  /* ================= acompanhar pedidos (geração e atualização) ================= */
  const timers = {};
  const pendentes = () => ler('gc_pendentes') || {};
  const marcarPendente = (cd, dados) => { const p = pendentes(); dados ? p[cd] = dados : delete p[cd]; guardar('gc_pendentes', p); };
  function acompanhar(cd, id, tipo, nome, uf) {
    marcarPendente(cd, {id, tipo, nome: nome || byCode[cd]?.n, uf: uf || byCode[cd]?.uf, desde: pendentes()[cd]?.desde || Date.now()});
    clearTimeout(timers[cd]);
    const tick = async () => {
      try {
        const p = await api.pedido(id);
        if (!p) { marcarPendente(cd, null); return; }
        if (pesquisaAtual?.cd === cd) { pesquisaAtual.estado = p.status === 'pronto' ? 'pronto' : p.status; pesquisaAtual.mensagem = p.mensagem; renderPesquisa(); }
        if (p.status === 'pronto') return concluir(cd, tipo);
        if (p.status === 'erro') {
          marcarPendente(cd, null);
          if (tipo === 'exportar' && byCode[cd]) { byCode[cd].arq = {estado: 'erro', mensagem: p.mensagem || 'erro ao preparar'}; redesenhar(cd); return; }
          if (pesquisaAtual?.cd === cd) { pesquisaAtual.estado = 'erro'; pesquisaAtual.mensagem = p.mensagem || 'A geração não deu certo.'; renderPesquisa(); }
          else toast(`Não consegui gerar ${nome || byCode[cd]?.n || cd}: ${p.mensagem || 'erro na geração'}`, 6000);
          return;
        }
      } catch { /* rede instável: tenta de novo no próximo ciclo */ }
      timers[cd] = setTimeout(tick, 7000);
    };
    timers[cd] = setTimeout(tick, 3000);
  }
  async function concluir(cd, tipo) {
    marcarPendente(cd, null);
    if (tipo === 'verificar') {                          // só conferência: relê o resultado, sem baixar o município de novo
      try { delete byCode[cd].verif; await consultarFontes(cd, 'consultar'); } catch { /* o cartão mostra o erro */ }
      return;
    }
    try {
      const [row] = await api.catalogo(cd);
      const m = incluirNaBase(montar(row)) || byCode[cd];
      if (m.detalhe) m.detalhe = false;                  // força baixar a versão nova
      delete m.verif;
      await carregarDetalhe(cd);
      if (tipo === 'exportar') { m.arq = null; m.arquivos = row.arquivos || null; }
      toast(`${m.n}: ${tipo === 'exportar' ? 'arquivos GIS prontos para baixar' : tipo === 'atualizar' ? 'dados atualizados' : 'dados gerados e guardados na base'}.`, 5000);
      if (pesquisaAtual?.cd === cd || selected === cd) { pesquisaAtual = null; window.abrirMunicipio(cd, true); }
    } catch (e) { console.error('Falha ao carregar o município pronto:', e); toast('Os dados ficaram prontos, mas não consegui carregá-los agora. Recarregue a página.', 6000); }
  }

  /* ================= tela "gerar dados" (município fora da base) ================= */
  let pesquisaAtual = null, contorno = null, relogio = null;
  const limparContorno = () => { if (contorno) { map.removeLayer(contorno); contorno = null; } };
  window.limparPesquisa = () => { pesquisaAtual = null; limparContorno(); clearInterval(relogio); document.querySelector('aside').classList.remove('pesquisa'); };
  async function mostrarContorno(cd) {
    limparContorno();
    let g = byCode[cd]?.g ? {type: 'Feature', geometry: byCode[cd].g} : null;
    if (!g) {
      try {
        const r = await fetch(`https://servicodados.ibge.gov.br/api/v3/malhas/municipios/${cd}?formato=application/vnd.geo+json&qualidade=minima`);
        const j = await r.json(); g = j.features ? j.features[0] : j;
      } catch { /* sem contorno: o mapa fica onde está */ }
    }
    if (!g || pesquisaAtual?.cd !== cd) return;
    contorno = L.geoJSON(g, {interactive: false, style: {color: css('--accent'), weight: 3, dashArray: '8 6', fillColor: css('--accent'), fillOpacity: .1}}).addTo(map);
    enquadrar(contorno.getBounds());
  }
  window.abrirPesquisa = async cd => {
    if (!SERVIDOR) { toast(`${byCode[cd]?.n || 'Este município'} ainda não tem dados na base.`); return; }
    const lista = await carregarLista();
    const i = lista.find(x => x.cd === cd);
    const nome = i?.nome || byCode[cd]?.n || cd, uf = i?.uf || '';
    if (selected) { selected = null; limparMancha(); munLayer.setStyle(styleMun); refreshVias(); }
    const pend = pendentes()[cd];
    pesquisaAtual = {cd, nome, uf, estado: pend ? 'fila' : 'inicial', desde: pend?.desde};
    $('viewList').hidden = true; $('viewDetail').hidden = false;
    document.querySelector('aside').classList.add('detail-open', 'pesquisa');
    if (telaPequena.matches) setSheet('meio');
    renderPesquisa(); mostrarContorno(cd);
    if (pend) acompanhar(cd, pend.id, pend.tipo, nome, uf);
  };
  async function gerar() {
    const p = pesquisaAtual; p.estado = 'enviando'; renderPesquisa();
    try {
      const r = await api.solicitar(p.cd, 'consultar');
      if (r.existe) {                                       // alguém acabou de gerar: só abrir
        const [row] = await api.catalogo(p.cd); incluirNaBase(montar(row)); pesquisaAtual = null; return window.abrirMunicipio(p.cd, true);
      }
      p.estado = r.estado || 'fila'; p.mensagem = r.mensagem; p.desde = Date.now();
      if (r.pedido) acompanhar(p.cd, r.pedido.id, 'gerar', p.nome, p.uf);
    } catch (e) { p.estado = 'erro'; p.mensagem = e.message; }
    renderPesquisa();
  }
  function renderPesquisa() {
    const p = pesquisaAtual; if (!p) return;
    const ativo = ['fila', 'processando', 'enviando'].includes(p.estado);
    const passos = ['Lendo os setores censitários urbanos do IBGE', 'Buscando as vias transitáveis no OpenStreetMap',
      'Recortando as vias nas manchas urbanas e medindo', 'Guardando na base'];
    let corpo;
    if (p.estado === 'inicial') corpo = `
      <p>Este município ainda <b>não está na base</b> do GIS Comercial.</p>
      <p>Ao gerar, o sistema usa o mesmo método dos demais: lê os <b>setores censitários urbanos do IBGE (2022)</b>, busca no
      <b>OpenStreetMap</b> as vias transitáveis por veículo, recorta dentro das manchas urbanas e mede. Leva de 1 a 10 minutos
      conforme o tamanho. Depois, <b>o município fica guardado e aparece para todos</b>.</p>
      ${SERVIDOR ? '' : '<div class="alert">A geração automática ainda não está ativada neste endereço.</div>'}
      <div class="acts"><button class="btn primary" id="btnGerar" ${SERVIDOR ? '' : 'disabled'}>Gerar dados de ${esc(p.nome)}</button></div>`;
    else if (ativo) corpo = `
      <div class="andamento"><i class="spin"></i><div><b>${p.estado === 'fila' ? 'Na fila de geração' : p.estado === 'enviando' ? 'Enviando o pedido…' : 'Gerando os dados…'}</b>
        <small>Tempo decorrido: <span id="decorrido">${tempo(p.desde)}</span></small></div></div>
      <ol class="passos">${passos.map((t, i) => `<li class="${p.estado === 'processando' && i < 3 ? 'em' : ''}">${t}</li>`).join('')}</ol>
      <p class="note">Pode fechar esta janela ou trocar de município: o pedido continua no servidor e o município entra na base quando ficar pronto.
      Ao reabrir o mapa neste aparelho, ele retoma o acompanhamento.</p>`;
    else if (p.estado === 'erro') corpo = `
      <div class="alert erro"><b>Não deu certo.</b> ${esc(p.mensagem || 'Erro na geração.')}</div>
      <div class="acts"><button class="btn primary" id="btnGerar">Tentar de novo</button></div>`;
    else corpo = '<p>Pronto! Abrindo o município…</p>';
    $('detail').innerHTML = `
      <div class="dtop"><button class="btn ghost" id="btnBack"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>Todos os municípios</button></div>
      <div class="dtitle"><h2>${esc(p.nome)}${p.uf ? ' · ' + esc(p.uf) : ''}</h2><p><span class="chip novo">Sem dados</span>Código IBGE ${p.cd}</p></div>
      ${corpo}`;
    $('btnBack').onclick = closeDetail;
    const b = el('btnGerar'); if (b) b.onclick = gerar;
    clearInterval(relogio);
    if (ativo) relogio = setInterval(() => { const s = el('decorrido'); if (s) s.textContent = tempo(p.desde); }, 1000);
  }
  const tempo = desde => { const s = Math.max(0, Math.round((Date.now() - (desde || Date.now())) / 1000)); return `${Math.floor(s / 60)}min ${String(s % 60).padStart(2, '0')}s`; };
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && pesquisaAtual && !document.querySelector('dialog[open]')) closeDetail(); });

  /* ================= barra de pesquisa ================= */
  const campo = el('busca'), caixa = document.createElement('div');
  caixa.id = 'resultados'; caixa.hidden = true; caixa.setAttribute('role', 'listbox');
  campo.parentElement.appendChild(caixa);
  let itens = [], ativoIdx = -1;
  const comeca = (a, q) => (a.startsWith(q) ? 0 : 1);
  async function sugerir() {
    const q = slug(campo.value.trim().toLowerCase());
    if (!SERVIDOR || q.length < 2) { caixa.hidden = true; return; }   // sem servidor, a busca só filtra a lista da base
    const lista = await carregarLista();
    const base = CO.filter(m => slug(m.n.toLowerCase()).includes(q)).sort((a, b) => comeca(slug(a.n.toLowerCase()), q) - comeca(slug(b.n.toLowerCase()), q)).slice(0, 5);
    const outros = lista.filter(x => !byCode[x.cd]?.co && x.s.includes(q)).sort((a, b) => comeca(a.s, q) - comeca(b.s, q) || a.nome.localeCompare(b.nome)).slice(0, 8);
    itens = [...base.map(m => ({cd: m.c, tipo: 'base'})), ...outros.map(x => ({cd: x.cd, tipo: 'novo'}))];
    ativoIdx = itens.length ? 0 : -1;
    const lin = (t, i, cd, nome, sub, tag) => `<button class="ri ${i === 0 ? 'on' : ''}" data-i="${i}" data-cd="${cd}" data-tipo="${t}" role="option"><span>${esc(nome)}<small>${esc(sub)}</small></span><em>${tag}</em></button>`;
    let i = 0, h = '';
    if (base.length) h += '<div class="rsec">Na base</div>' + base.map(m => lin('base', i++, m.c, m.n, `${m.uf || 'PE'} · ${fmt(m.vias, 0)} km de vias`, 'Abrir')).join('');
    if (outros.length) h += '<div class="rsec">Outros municípios do Brasil</div>' + outros.map(x => lin('novo', i++, x.cd, x.nome, x.uf, SERVIDOR ? 'Gerar dados' : 'Sem dados')).join('');
    caixa.innerHTML = h || '<div class="rsec">Nenhum município encontrado</div>';
    caixa.hidden = false;
  }
  function escolher(i) {
    const it = itens[i]; if (!it) return;
    campo.value = ''; caixa.hidden = true; renderList(); campo.blur();
    it.tipo === 'base' ? window.abrirMunicipio(it.cd, true) : window.abrirPesquisa(it.cd);
  }
  const marcar = n => { ativoIdx = (n + itens.length) % itens.length; caixa.querySelectorAll('.ri').forEach(b => b.classList.toggle('on', +b.dataset.i === ativoIdx)); caixa.querySelector('.ri.on')?.scrollIntoView({block: 'nearest'}); };
  campo.addEventListener('input', sugerir);
  campo.addEventListener('focus', () => { if (!SERVIDOR) return; carregarLista(); if (campo.value.trim().length >= 2) sugerir(); });
  campo.addEventListener('keydown', e => {
    if (caixa.hidden && e.key !== 'ArrowDown') return;
    if (e.key === 'ArrowDown') { e.preventDefault(); caixa.hidden ? sugerir() : marcar(ativoIdx + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); marcar(ativoIdx - 1); }
    else if (e.key === 'Enter') { e.preventDefault(); escolher(ativoIdx); }
    else if (e.key === 'Escape') { caixa.hidden = true; }
  });
  caixa.addEventListener('mousedown', e => { const b = e.target.closest('.ri'); if (b) { e.preventDefault(); escolher(+b.dataset.i); } });
  document.addEventListener('click', e => { if (!e.target.closest('.field')) caixa.hidden = true; });
  if (SERVIDOR) {
    campo.placeholder = 'Buscar qualquer município do Brasil';
    setTimeout(carregarLista, 1500);          // deixa a lista pronta antes da primeira digitação
  }

  /* links diretos: ?q=<texto> abre a busca já preenchida · ?pesquisa=<código IBGE> abre a tela de gerar dados */
  if (SERVIDOR) {
    const q = PARAMS.get('q'), pq = PARAMS.get('pesquisa');
    if (q) setTimeout(() => { campo.value = q; sugerir(); }, 600);
    if (pq && /^\d{7}$/.test(pq)) setTimeout(() => { if (!byCode[pq]?.co) window.abrirPesquisa(pq); }, 600);
  }

  /* ================= catálogo compartilhado e pedidos em andamento ================= */
  (async () => {
    if (!SERVIDOR) return;
    try {
      const linhas = await api.catalogo();
      linhas.forEach(r => incluirNaBase(montar(r), true));
      reconstruir();
      new Set(linhas.map(r => r.uf)).forEach(carregarMalhaUf);
      const cd = PARAMS.get('mun');
      if (cd && !selected && byCode[cd]?.co) window.abrirMunicipio(cd, !PARAMS.get('zoom'));
      else if (selected) { consultarFontes(selected); renderDetail(byCode[selected]); }
    } catch (e) { console.warn('Catálogo indisponível:', e.message); }
    Object.entries(pendentes()).forEach(([cd, p]) => acompanhar(cd, p.id, p.tipo, p.nome, p.uf));   // retoma pedidos deste aparelho
  })();
})();
