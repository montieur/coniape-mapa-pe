/* Relatórios PDF gerados no navegador (jsPDF). Usa os globais D, CO, byCode, fmt, slug e toast do index.html. */
/* ===== PDF gerado (jsPDF) ===== */
const ACCENT = [15, 110, 140];
function pdfHeader(doc, title, sub) {
  doc.setFillColor(...ACCENT); doc.rect(0, 0, 210, 22, 'F');
  doc.setTextColor(255); doc.setFont('helvetica', 'bold'); doc.setFontSize(14); doc.text(title, 14, 10);
  doc.setFont('helvetica', 'normal'); doc.setFontSize(9); doc.text(sub, 14, 16.5);
  doc.setTextColor(30);
}
function pdfFooter(doc) {
  const n = doc.getNumberOfPages();
  for (let i = 1; i <= n; i++) {
    doc.setPage(i); doc.setFontSize(7.5); doc.setTextColor(120);
    doc.text(`CONIAPE · Área urbana: setores IBGE 2022 (CD_SIT 1-3) · Vias: OpenStreetMap · Malha municipal IBGE 2024 · Projeção SIRGAS 2000 / UTM 25S`, 14, 289);
    doc.text(`Gerado em ${new Date().toLocaleString('pt-BR')} · pág. ${i}/${n}`, 196, 289, {align: 'right'});
  }
}
/* desenha geometrias lon/lat numa caixa da página (equiretangular com correção de latitude) */
function drawGeoms(doc, box, layers) {
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  const each = (g, f) => { const polys = g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : null; if (polys) polys.forEach(p => p.forEach(r => f(r))); };
  layers.filter(l => l.fit).forEach(l => l.geoms.forEach(g => each(g, r => r.forEach(([x, y]) => { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }))));
  const k = Math.cos((y0 + y1) / 2 * Math.PI / 180);
  const s = Math.min(box.w / ((x1 - x0) * k), box.h / (y1 - y0));
  const ox = box.x + (box.w - (x1 - x0) * k * s) / 2, oy = box.y + (box.h - (y1 - y0) * s) / 2;
  const P = ([x, y]) => [ox + (x - x0) * k * s, oy + (y1 - y) * s];
  const path = (pts, style) => { if (pts.length < 2) return; const [sx, sy] = P(pts[0]); const d = []; let [px, py] = [sx, sy];
    for (let i = 1; i < pts.length; i++) { const [qx, qy] = P(pts[i]); d.push([qx - px, qy - py]); px = qx; py = qy; }
    doc.lines(d, sx, sy, [1, 1], style, style !== 'S'); };
  layers.forEach(l => {
    doc.setLineWidth(l.lw ?? .2); doc.setDrawColor(...l.stroke); if (l.fill) doc.setFillColor(...l.fill);
    if (l.lines) l.lines.forEach(pts => path(pts, 'S'));
    else l.geoms.forEach(g => each(g, r => path(r, l.fill ? 'FD' : 'S')));
  });
  doc.setDrawColor(200); doc.setLineWidth(.2); doc.rect(box.x, box.y, box.w, box.h);
}
function save(doc, name) { doc.save(name); toast('PDF gerado'); }

function gerarPdfMunicipio(m) {
  const {jsPDF} = window.jspdf; const doc = new jsPDF({unit: 'mm', format: 'a4'});
  pdfHeader(doc, `Relatório CONIAPE · ${m.n} – PE`, `Código IBGE ${m.c} · RGI ${m.rgi} · Região intermediária ${m.rgint}`);
  const urbs = D.urb.filter(u => u.c === m.c);
  const vias = (D.vias[m.c] || []).map(([, , f]) => { const p = []; for (let i = 0; i < f.length; i += 2) p.push([f[i], f[i + 1]]); return p; });
  drawGeoms(doc, {x: 14, y: 28, w: 182, h: 120}, [
    {geoms: [m.g], stroke: [90, 90, 90], fill: [240, 243, 246], lw: .4, fit: true},
    {geoms: urbs.map(u => u.g), stroke: [232, 118, 44], fill: [250, 214, 190], lw: .25},
    {lines: vias, stroke: [192, 57, 43], lw: .08},
  ]);
  doc.setFontSize(7.5); doc.setTextColor(90);
  doc.text('Limite municipal (cinza) · áreas urbanas (laranja) · vias urbanas (vermelho)', 14, 152);
  doc.autoTable({
    startY: 157, theme: 'grid', headStyles: {fillColor: ACCENT}, styles: {fontSize: 9},
    columnStyles: {1: {halign: 'right'}},
    head: [['Indicador', 'Valor']],
    body: [
      ['Área urbana (setores IBGE 2022)', fmt(m.urb) + ' km²'],
      ['Vias urbanas (OSM)', fmt(m.vias) + ' km'],
      ['Densidade de vias', fmt(m.dens) + ' km/km²'],
      ['Território – área oficial IBGE', fmt(m.aI, 3) + ' km²'],
      ['Território – área planimétrica UTM 25S', fmt(m.aU, 3) + ' km²'],
      ['Área urbana / território', fmt(m.perc) + ' %'],
      ['Área rural (setores)', m.rur ? fmt(m.rur) + ' km²' : '–'],
      ['Setores urbanos', m.set ?? '–'], ['Distritos / manchas', m.dist ?? '–'],
    ],
  });
  const dist = D.distritos.filter(d => d.CD_MUN === m.c);
  if (dist.length) doc.autoTable({
    startY: doc.lastAutoTable.finalY + 6, theme: 'grid', headStyles: {fillColor: ACCENT}, styles: {fontSize: 9},
    columnStyles: {1: {halign: 'right'}, 2: {halign: 'right'}},
    head: [['Distrito / mancha urbana', 'Área (km²)', 'Vias (km)']],
    body: dist.map(d => [d.distrito, fmt(d.area_km2), fmt(d.vias_km)]),
  });
  pdfFooter(doc); save(doc, `Relatorio_mapa_${slug(m.n)}_PE.pdf`);
}

function gerarPdfGeral() {
  const {jsPDF} = window.jspdf; const doc = new jsPDF({unit: 'mm', format: 'a4'});
  pdfHeader(doc, 'Relatório geral CONIAPE · Pernambuco', `${CO.length} municípios · área urbana e extensão de vias urbanas`);
  drawGeoms(doc, {x: 14, y: 28, w: 182, h: 78}, [
    {geoms: D.mun.filter(m => !m.co).map(m => m.g), stroke: [205, 210, 216], fill: [244, 245, 247], lw: .1, fit: true},
    {geoms: CO.map(m => m.g), stroke: [255, 255, 255], fill: [95, 176, 198], lw: .15, fit: true},
  ]);
  doc.setFontSize(7.5); doc.setTextColor(90); doc.text('Municípios do CONIAPE em destaque (azul) sobre a malha municipal de PE (IBGE 2024)', 14, 110);
  const tU = CO.reduce((s, m) => s + m.urb, 0), tV = CO.reduce((s, m) => s + m.vias, 0);
  const rows = [...CO].sort((a, b) => a.n.localeCompare(b.n));
  doc.autoTable({
    startY: 114, theme: 'striped', headStyles: {fillColor: ACCENT}, styles: {fontSize: 8, cellPadding: 1.4},
    columnStyles: {1: {halign: 'right'}, 2: {halign: 'right'}, 3: {halign: 'right'}, 4: {halign: 'right'}, 5: {halign: 'right'}},
    head: [['Município', 'Território IBGE (km²)', 'Área urbana (km²)', 'Vias (km)', 'km vias/km²', '% urbano']],
    body: rows.map(m => [m.n, fmt(m.aI, 1), fmt(m.urb), fmt(m.vias), fmt(m.dens), fmt(m.perc)]),
    foot: [['TOTAL', fmt(CO.reduce((s, m) => s + m.aI, 0), 1), fmt(tU), fmt(tV), fmt(tV / tU), '']],
    footStyles: {fillColor: [230, 236, 240], textColor: 20, fontStyle: 'bold', halign: 'right'},
  });
  pdfFooter(doc); save(doc, 'Relatorio_geral_CONIAPE_PE.pdf');
}
