/* Relatórios PDF gerados no navegador (jsPDF). Usa os globais D, CO, byCode, fmt, slug e toast do index.html. */
const ACCENT = [5, 119, 189];                    // azul tecgeo (#0577bd) para cabeçalhos de tabela
const NAVY = [16, 54, 90];                       // azul-marinho do logotipo
const MARCA = [[2, 156, 254], [40, 176, 229], [108, 216, 182], [144, 236, 158]];   // paleta tecgeo
let LOGO = null;                                 // logotipo em PNG, preparado uma vez a partir do SVG
async function prepararLogo() {
  if (LOGO !== null) return;
  LOGO = await new Promise(res => {
    const im = new Image();
    im.onload = () => { const cv = Object.assign(document.createElement('canvas'), {width: 364, height: 334});
      cv.getContext('2d').drawImage(im, 0, 0, 364, 334); try { res(cv.toDataURL('image/png')); } catch (e) { res(''); } };
    im.onerror = () => res('');
    im.src = 'icones/logo-mark.svg';
  });
}
/* mapas base dos relatórios (o usuário escolhe; todos liberam CORS para o canvas). Camadas de cima = rótulos. */
const PDF_BASES = {
  'Satélite': {max: 18, attr: 'Imagem: Esri, Maxar, Earthstar Geographics · rótulos: Esri', escuro: true, tiles: [
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}']},
  'Cinza claro': {max: 16, attr: 'Mapa base: Esri, HERE, Garmin, © colaboradores OpenStreetMap', tiles: [
    'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}']},
  'OpenStreetMap': {max: 18, attr: '© colaboradores OpenStreetMap', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png']},
};
let pdfBase = 'Satélite';
window.definirBasePdf = nome => { if (PDF_BASES[nome]) pdfBase = nome; };
const baseAtualPdf = () => PDF_BASES[pdfBase];
/* cores das linhas conforme o fundo: claras sobre o satélite, escuras sobre os mapas claros */
const corLimite = () => baseAtualPdf().escuro ? [255, 255, 255] : [15, 70, 90];
const corVizinhos = () => baseAtualPdf().escuro ? [225, 230, 235] : [150, 158, 168];

function pdfHeader(doc, title, sub) {
  doc.setFillColor(...NAVY); doc.rect(0, 0, 210, 22, 'F');
  MARCA.forEach((c, i) => { doc.setFillColor(...c); doc.rect(i * 52.5, 22, 52.5, 1.2, 'F'); });   // faixa com as cores da marca
  const x = LOGO ? 25 : 14;
  if (LOGO) doc.addImage(LOGO, 'PNG', 12, 5, 10.9, 10);
  doc.setTextColor(255); doc.setFont('helvetica', 'bold'); doc.setFontSize(14); doc.text(title, x, 10);
  doc.setFont('helvetica', 'normal'); doc.setFontSize(9); doc.text(doc.splitTextToSize(sub, 196 - x - 22)[0], x, 16.5);
  doc.setFont('helvetica', 'bold'); doc.setFontSize(12); doc.text('tecgeo', 196, 12, {align: 'right'});
  doc.setFont('helvetica', 'normal'); doc.setTextColor(30);
}
function pdfFooter(doc) {
  const n = doc.getNumberOfPages();
  for (let i = 1; i <= n; i++) {
    doc.setPage(i); doc.setFontSize(7.5); doc.setTextColor(120);
    doc.text(`GIS Comercial · tecgeo · Área urbana: setores IBGE 2022 (CD_SIT 1-3) · Vias: OpenStreetMap, transitáveis por veículo, recortadas nas manchas`, 14, 285.5);
    doc.text(`Malha municipal IBGE 2024 · Medições em SIRGAS 2000 / UTM do fuso de cada município`, 14, 289);
    doc.text(`Gerado em ${new Date().toLocaleString('pt-BR')} · pág. ${i}/${n}`, 196, 289, {align: 'right'});
  }
}

/* ---------- mapa no PDF (Web Mercator, igual aos tiles) ---------- */
const merc = ([lon, lat]) => { const s = Math.sin(lat * Math.PI / 180); return [(lon + 180) / 360, .5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)]; };
const eachRing = (g, f) => { const polys = g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : []; polys.forEach(p => p.forEach(f)); };
const loadImg = url => new Promise(res => {
  const im = new Image(); im.crossOrigin = 'anonymous';
  const t = setTimeout(() => res(null), 10000);
  im.onload = () => { clearTimeout(t); res(im); }; im.onerror = () => { clearTimeout(t); res(null); };
  im.src = url;
});

/* monta o mapa base da janela [x0,y0,x1,y1] (unidades de mundo 0..1) num canvas com ~targetPx de largura */
async function basemapImage(x0, y0, x1, y1, targetPx) {
  const z = Math.max(3, Math.min(baseAtualPdf().max, Math.round(Math.log2(targetPx / ((x1 - x0) * 256)))));
  const n = 2 ** z, W = Math.round((x1 - x0) * 256 * n), H = Math.round((y1 - y0) * 256 * n);
  const cv = Object.assign(document.createElement('canvas'), {width: W, height: H});
  const ctx = cv.getContext('2d');
  ctx.fillStyle = '#e9ecef'; ctx.fillRect(0, 0, W, H);
  const tx0 = Math.floor(x0 * n), tx1 = Math.floor(x1 * n), ty0 = Math.floor(y0 * n), ty1 = Math.floor(y1 * n);
  let ok = 0;
  for (const tpl of baseAtualPdf().tiles) {
    const jobs = [];
    for (let tx = tx0; tx <= tx1; tx++) for (let ty = ty0; ty <= ty1; ty++)
      jobs.push(loadImg(tpl.replace('{z}', z).replace('{x}', tx).replace('{y}', ty)).then(im => {
        if (im) { ctx.drawImage(im, Math.round(tx * 256 - x0 * 256 * n), Math.round(ty * 256 - y0 * 256 * n)); ok++; }
      }));
    await Promise.all(jobs);
  }
  try { return ok ? cv.toDataURL('image/jpeg', .86) : null; } catch (e) { return null; }   // canvas "sujo" = sem CORS
}

/* barra de escala: escolhe um comprimento redondo perto de 1/5 da largura do mapa */
function scaleBar(doc, box, bw, latC) {
  const mPerMm = 40075016.686 * Math.cos(latC * Math.PI / 180) * bw / box.w;
  const target = mPerMm * box.w / 5, p = 10 ** Math.floor(Math.log10(target));
  const len = [1, 2, 5, 10].map(k => k * p).reverse().find(v => v <= target) || p;
  const mm = len / mPerMm, x = box.x + 4, y = box.y + box.h - 5;
  doc.setFillColor(255, 255, 255); doc.setGState(new doc.GState({opacity: .8}));
  doc.rect(x - 2, y - 5, mm + 4 + 14, 8, 'F'); doc.setGState(new doc.GState({opacity: 1}));
  doc.setFillColor(40, 40, 40); doc.rect(x, y, mm / 2, 1.2, 'F');
  doc.setDrawColor(40, 40, 40); doc.setLineWidth(.25); doc.rect(x, y, mm, 1.2, 'S');
  doc.setFontSize(6.5); doc.setTextColor(40);
  doc.text('0', x, y - 1, {align: 'center'});
  doc.text(len >= 1000 ? `${fmt(len / 1000, 0)} km` : `${fmt(len, 0)} m`, x + mm, y - 1, {align: 'center'});
  // seta do norte
  doc.setFontSize(8); doc.setFont('helvetica', 'bold'); doc.text('N', box.x + box.w - 6, box.y + 7, {align: 'center'});
  doc.setFont('helvetica', 'normal'); doc.setFillColor(40, 40, 40);
  doc.triangle(box.x + box.w - 6, box.y + 8.5, box.x + box.w - 7.6, box.y + 12.5, box.x + box.w - 4.4, box.y + 12.5, 'F');
}

/* camadas: {geoms|lines, stroke, fill?, fillOp?, lw?, fit?} */
async function drawMap(doc, box, layers, {pad = .06, px = 1600} = {}) {
  let x0 = 1, y0 = 1, x1 = 0, y1 = 0;
  layers.filter(l => l.fit).forEach(l => l.geoms.forEach(g => eachRing(g, r => r.forEach(c => {
    const [x, y] = merc(c); x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
  }))));
  // margem e proporção da caixa
  let bw = (x1 - x0) * (1 + 2 * pad), bh = (y1 - y0) * (1 + 2 * pad);
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, asp = box.w / box.h;
  if (bw / bh < asp) bw = bh * asp; else bh = bw / asp;
  x0 = cx - bw / 2; x1 = cx + bw / 2; y0 = cy - bh / 2; y1 = cy + bh / 2;

  const img = await basemapImage(x0, y0, x1, y1, px);
  if (img) doc.addImage(img, 'JPEG', box.x, box.y, box.w, box.h);
  else { doc.setFillColor(244, 245, 247); doc.rect(box.x, box.y, box.w, box.h, 'F'); }

  const P = c => { const [x, y] = merc(c); return [box.x + (x - x0) / bw * box.w, box.y + (y - y0) / bh * box.h]; };
  const path = (pts, style) => {
    if (pts.length < 2) return;
    const [sx, sy] = P(pts[0]); const d = []; let px_ = sx, py_ = sy;
    for (let i = 1; i < pts.length; i++) { const [qx, qy] = P(pts[i]); d.push([qx - px_, qy - py_]); px_ = qx; py_ = qy; }
    doc.lines(d, sx, sy, [1, 1], style, style !== 'S');
  };
  doc.saveGraphicsState();
  doc.rect(box.x, box.y, box.w, box.h, null); doc.clip(); doc.discardPath();   // nada vaza da moldura
  layers.forEach(l => {
    doc.setLineWidth(l.lw ?? .2); doc.setDrawColor(...l.stroke);
    if (l.lines) { l.lines.forEach(pts => path(pts, 'S')); return; }
    if (l.fill) {   // preenchimento translúcido para o mapa base aparecer
      doc.setFillColor(...l.fill); doc.setGState(new doc.GState({opacity: l.fillOp ?? 1}));
      l.geoms.forEach(g => eachRing(g, r => path(r, 'F')));
      doc.setGState(new doc.GState({opacity: 1}));
    }
    l.geoms.forEach(g => eachRing(g, r => path(r, 'S')));
  });
  doc.restoreGraphicsState();

  const latC = Math.atan(Math.sinh(Math.PI * (1 - 2 * cy))) * 180 / Math.PI;
  scaleBar(doc, box, bw, latC);
  doc.setDrawColor(190); doc.setLineWidth(.25); doc.rect(box.x, box.y, box.w, box.h);
  doc.setFontSize(6); doc.setTextColor(110);
  doc.text(img ? baseAtualPdf().attr : 'Mapa base indisponível (sem conexão)', box.x + box.w - 1.5, box.y + box.h - 1.5, {align: 'right'});
}

function save(doc, name) {
  if (window.__previa) { window.__previa = false; return window.mostrarPrevia(doc, name); }   // ver antes de baixar
  doc.save(name); toast('PDF gerado');
}

/* uma página de município (cabeçalho, mapa, indicadores e distritos) no documento aberto */
async function paginaMunicipio(doc, m) {
  const uf = m.uf || 'PE';
  pdfHeader(doc, `GIS Comercial · ${m.n} – ${uf}`, `Código IBGE ${m.c}` + (m.rgi ? ` · Região imediata de ${m.rgi}` : '') + (m.rgint ? ` · Região intermediária de ${m.rgint}` : ''));
  const urbs = D.urb.filter(u => u.c === m.c);
  const vias = (D.vias[m.c] || []).map(([, , f]) => { const p = []; for (let i = 0; i < f.length; i += 2) p.push([f[i], f[i + 1]]); return p; });
  await drawMap(doc, {x: 14, y: 28, w: 182, h: 120}, [
    {geoms: D.mun.filter(x => x.c !== m.c).map(x => x.g), stroke: corVizinhos(), lw: .15},   // vizinhos
    {geoms: urbs.map(u => u.g), stroke: [222, 105, 30], fill: [232, 118, 44], fillOp: .32, lw: .25},
    {lines: vias, stroke: [192, 57, 43], lw: .12},
    {geoms: [m.g], stroke: corLimite(), lw: .7, fit: true},
  ], {px: 1100});   // ~150 dpi: rótulos do mapa base legíveis no A4
  doc.setFontSize(7.5); doc.setTextColor(90);
  doc.text(`Limite municipal (${baseAtualPdf().escuro ? 'branco' : 'azul escuro'}) · municípios vizinhos (cinza) · áreas urbanas (laranja) · vias transitáveis (vermelho)`, 14, 152);
  doc.autoTable({
    startY: 157, theme: 'grid', headStyles: {fillColor: ACCENT}, margin: {bottom: 16}, styles: {fontSize: 9},
    columnStyles: {1: {halign: 'right'}},
    head: [['Indicador', 'Valor']],
    body: [
      ['Área urbana (setores IBGE 2022)', fmt(m.urb) + ' km²'],
      ['Vias transitáveis dentro das manchas urbanas', fmt(m.vias) + ' km'],
      ...(m.rev ? [[`Vias – critério CONIAPE original (via inteira${m.rev.motivo ? ', extração incompleta' : ''})`, fmt(m.rev.orig) + ' km']] : []),
      ['Densidade de vias', fmt(m.dens) + ' km/km²'],
      ['Território – área oficial IBGE', fmt(m.aI, 3) + ' km²'],
      [`Território – área planimétrica UTM ${m.zona ?? 25}S`, fmt(m.aU, 3) + ' km²'],
      ['Área urbana / território', fmt(m.perc) + ' %'],
      ['Área rural (setores)', m.rur ? fmt(m.rur) + ' km²' : '–'],
      ['Setores urbanos', m.set ?? '–'], ['Distritos / manchas', m.dist ?? '–'],
    ],
  });
  const dist = D.distritos.filter(d => d.CD_MUN === m.c).sort((a, b) => b.vias_km - a.vias_km);
  if (dist.length) doc.autoTable({
    startY: doc.lastAutoTable.finalY + 6, theme: 'grid', headStyles: {fillColor: ACCENT}, margin: {bottom: 16}, styles: {fontSize: 9},
    columnStyles: {1: {halign: 'right'}, 2: {halign: 'right'}},
    head: [['Distrito / mancha urbana', 'Área (km²)', 'Vias (km)']],
    body: dist.map(d => [d.distrito, fmt(d.area_km2), fmt(d.vias_km)]),
  });
}

async function gerarPdfMunicipio(m) {
  toast('Gerando PDF com mapa base…', 0);
  await prepararLogo();
  const uf = m.uf || 'PE';
  const {jsPDF} = window.jspdf; const doc = new jsPDF({unit: 'mm', format: 'a4'});
  await paginaMunicipio(doc, m);
  pdfFooter(doc); save(doc, `Relatorio_mapa_${slug(m.n)}_${uf}.pdf`);
}

/* PDF único com os municípios escolhidos: resumo (mapa, totais e tabela comparativa) + uma página por município (opcional) */
async function gerarPdfSelecao(lista, {paginas = true} = {}) {
  await prepararLogo();
  const {jsPDF} = window.jspdf; const doc = new jsPDF({unit: 'mm', format: 'a4'});
  const ms = [...lista].sort((a, b) => (a.uf || 'PE').localeCompare(b.uf || 'PE') || a.n.localeCompare(b.n));
  const ufs = [...new Set(ms.map(m => m.uf || 'PE'))];
  const marcados = new Set(ms.map(m => m.c));
  if (paginas && window.garantirDetalhe) {                    // vias e manchas dos municípios que ainda não foram abertos
    for (let i = 0; i < ms.length; i++) {
      if (!ms[i].detalhe) { toast(`Carregando dados ${i + 1}/${ms.length}…`, 0); await window.garantirDetalhe(ms[i].c); }
    }
  }
  toast('Gerando PDF com mapa base…', 0);
  pdfHeader(doc, 'GIS Comercial · Relatório de municípios',
    `${ms.length} município${ms.length > 1 ? 's' : ''} · ${ufs.join(', ')} · área urbana e vias transitáveis dentro das manchas urbanas`);
  await drawMap(doc, {x: 14, y: 28, w: 182, h: 80}, [
    {geoms: D.mun.filter(x => !marcados.has(x.c)).map(x => x.g), stroke: corVizinhos(), lw: .1},
    {geoms: ms.map(m => m.g), stroke: [255, 255, 255], fill: [2, 156, 254], fillOp: .55, lw: .15, fit: true},
  ], {pad: .06, px: 1300});
  doc.setFontSize(7.5); doc.setTextColor(90);
  doc.text('Municípios selecionados em destaque (azul) sobre a malha municipal do IBGE 2024', 14, 112);

  const tT = ms.reduce((s, m) => s + (m.aI || 0), 0), tU = ms.reduce((s, m) => s + (m.urb || 0), 0), tV = ms.reduce((s, m) => s + (m.vias || 0), 0);
  const kpis = [['Municípios', String(ms.length)], ['Área urbana', fmt(tU) + ' km²'], ['Vias transitáveis', fmt(tV) + ' km'], ['Densidade de vias', fmt(tU ? tV / tU : 0) + ' km/km²']];
  const kw = (182 - 3 * 4) / 4;
  kpis.forEach(([rot, val], i) => {
    const x = 14 + i * (kw + 4);
    doc.setFillColor(225, 243, 254); doc.roundedRect(x, 116, kw, 17, 2, 2, 'F');
    doc.setTextColor(90); doc.setFontSize(7.5); doc.text(rot, x + 3, 121.5);
    doc.setTextColor(...NAVY); doc.setFont('helvetica', 'bold'); doc.setFontSize(12); doc.text(val, x + 3, 129);
    doc.setFont('helvetica', 'normal');
  });
  doc.setTextColor(30);

  const comOrig = ms.some(m => m.rev);
  const col = {halign: 'right'};
  doc.autoTable({
    startY: 138, theme: 'striped', headStyles: {fillColor: ACCENT}, margin: {bottom: 16}, styles: {fontSize: 8, cellPadding: 1.4},
    columnStyles: comOrig ? {2: col, 3: col, 4: col, 5: col, 6: col, 7: col} : {2: col, 3: col, 4: col, 5: col, 6: col},
    head: [['Município', 'UF', 'Território IBGE (km²)', 'Área urbana (km²)', 'Vias transitáveis (km)', ...(comOrig ? ['Vias CONIAPE orig. (km)'] : []), 'km vias/km²', '% urbano']],
    body: ms.map(m => [m.n, m.uf || 'PE', fmt(m.aI, 1), fmt(m.urb), fmt(m.vias), ...(comOrig ? [m.rev ? fmt(m.rev.orig) : '–'] : []), fmt(m.dens), fmt(m.perc)]),
    foot: [['TOTAL', '', fmt(tT, 1), fmt(tU), fmt(tV), ...(comOrig ? [fmt(ms.reduce((s, m) => s + (m.rev ? m.rev.orig : m.vias), 0))] : []), fmt(tU ? tV / tU : 0), fmt(tT ? tU / tT * 100 : 0)]],
    footStyles: {fillColor: [230, 236, 240], textColor: 20, fontStyle: 'bold', halign: 'right'},
  });
  const marca = (titulo, pagina) => { try { doc.outline.add(null, titulo, {pageNumber: pagina}); } catch (e) { /* marcador é só conveniência */ } };
  marca('Resumo', 1);
  if (paginas) {
    for (let i = 0; i < ms.length; i++) {
      toast(`Montando página ${i + 1}/${ms.length}: ${ms[i].n}…`, 0);
      doc.addPage();
      marca(`${ms[i].n} – ${ms[i].uf || 'PE'}`, doc.getNumberOfPages());
      await paginaMunicipio(doc, ms[i]);
    }
  }
  const nome = ufs.length === 1 ? `${ufs[0]}_` : '';
  pdfFooter(doc); save(doc, `Relatorio_municipios_GIS_Comercial_${nome}${ms.length}_municipios.pdf`);
}
