/* Renderiza o MANUAL.md (mesmo arquivo exibido no GitHub) dentro de um elemento da página.
   Usado pela janela do manual no index.html e pela página manual.html (base do PDF). */
(function () {
  const MARKED = 'https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js';
  let marcado = null;

  const carregarMarked = () => marcado ??= new Promise((ok, falha) => {
    if (window.marked) return ok(window.marked);
    const s = Object.assign(document.createElement('script'), {src: MARKED});
    s.onload = () => ok(window.marked); s.onerror = () => falha(new Error('marked'));
    document.head.appendChild(s);
  });

  /* mesmo identificador de âncora que o GitHub gera, para os links internos do .md funcionarem nos dois lugares */
  const slugGitHub = t => t.trim().toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, '').replace(/\s/g, '-');

  window.renderManual = async function (alvo, {toc, rolagem} = {}) {
    const [md, marked] = await Promise.all([
      fetch('MANUAL.md', {cache: 'no-cache'}).then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.text(); }),
      carregarMarked(),
    ]);
    alvo.innerHTML = marked.parse(md);
    alvo.querySelectorAll('h1, h2, h3').forEach(h => { h.id = slugGitHub(h.textContent); });
    // links externos em nova aba; âncoras internas rolam dentro do próprio contêiner
    alvo.querySelectorAll('a[href]').forEach(a => {
      const href = a.getAttribute('href');
      if (href.startsWith('#')) {
        a.addEventListener('click', e => { e.preventDefault(); irPara(alvo, href.slice(1), rolagem); });
      } else if (/^https?:/.test(href)) { a.target = '_blank'; a.rel = 'noopener'; }
    });
    // imagens: clicar abre em tamanho real
    alvo.querySelectorAll('img').forEach(im => {
      im.loading = 'lazy';
      im.addEventListener('click', () => window.open(im.src, '_blank'));
    });
    if (toc) {
      toc.innerHTML = [...alvo.querySelectorAll('h2')].map(h =>
        `<a href="#${h.id}">${h.textContent.replace(/^Parte (\d+):\s*/, '$1. ')}</a>`).join('');
      toc.querySelectorAll('a').forEach(a => a.addEventListener('click', e => {
        e.preventDefault(); irPara(alvo, a.getAttribute('href').slice(1), rolagem);
      }));
    }
    return alvo;
  };

  function irPara(alvo, id, rolagem) {
    const el = alvo.querySelector('#' + CSS.escape(decodeURIComponent(id)));
    if (!el) return;
    if (rolagem) rolagem.scrollTop += el.getBoundingClientRect().top - rolagem.getBoundingClientRect().top - 8;
    else el.scrollIntoView();
  }
  window.irParaManual = irPara;
})();
