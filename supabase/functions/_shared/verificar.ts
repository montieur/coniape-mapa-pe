// Verifica se as fontes de um município mudaram desde que ele foi gerado.
// Sem dependências de Deno: roda igual no Node (testes) e na Edge Function.

export interface Fontes {
  ibge_setores?: { url: string; last_modified?: string | null; content_length?: number | null };
  osm?: { base?: string | null; bbox?: [number, number, number, number]; endpoint?: string | null; vias_total?: number };
}

export interface Verificacao {
  verificado_em: string;
  mudou: boolean | null;          // null = não deu para verificar
  ibge: { mudou: boolean | null; gerado: string | null; atual: string | null; erro?: string };
  osm: { mudou: boolean | null; vias_alteradas: number | null; desde: string | null; percentual?: number | null; erro?: string };
  resumo: string;
}

const TIPOS = "motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|" +
  "tertiary|tertiary_link|unclassified|residential|living_street|service|road|track";
export const ENDPOINTS = [
  "https://overpass.openstreetmap.fr/api/interpreter", "https://z.overpass-api.de/api/interpreter",
  "https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
];
const UA = { "User-Agent": "GIS-Comercial/1.0 (TECGEO; geoprocessamento)" };

const com_tempo = (ms: number) => AbortSignal.timeout(ms);

export async function checarIbge(f: Fontes["ibge_setores"]): Promise<Verificacao["ibge"]> {
  if (!f?.url) return { mudou: null, gerado: null, atual: null, erro: "fonte do IBGE não registrada" };
  try {
    const r = await fetch(f.url, { method: "HEAD", headers: UA, signal: com_tempo(20000) });
    if (!r.ok) return { mudou: null, gerado: f.last_modified ?? null, atual: null, erro: `HTTP ${r.status}` };
    const lm = r.headers.get("last-modified");
    const len = Number(r.headers.get("content-length") ?? 0);
    const mudouData = !!f.last_modified && !!lm && new Date(lm).getTime() !== new Date(f.last_modified).getTime();
    const mudouTam = !!f.content_length && !!len && len !== f.content_length;
    return { mudou: mudouData || mudouTam, gerado: f.last_modified ?? null, atual: lm };
  } catch (e) {
    return { mudou: null, gerado: f.last_modified ?? null, atual: null, erro: String((e as Error).message ?? e) };
  }
}

export async function checarOsm(f: Fontes["osm"], endpoints: string[] = ENDPOINTS): Promise<Verificacao["osm"]> {
  if (!f?.base || !f.bbox) return { mudou: null, vias_alteradas: null, desde: null, erro: "extração do OSM não registrada" };
  const [w, s, e, n] = f.bbox;
  const q = `[out:json][timeout:60];way["highway"~"^(${TIPOS})$"](newer:"${f.base}")(${s},${w},${n},${e});out count;`;
  let ultimo = "";
  for (const ep of endpoints) {
    try {
      const r = await fetch(ep, {
        method: "POST", headers: { ...UA, "Content-Type": "application/x-www-form-urlencoded" },
        body: "data=" + encodeURIComponent(q), signal: com_tempo(45000),
      });
      if (!r.ok) { ultimo = `HTTP ${r.status}`; continue; }
      const j = await r.json();
      const total = Number(j?.elements?.[0]?.tags?.ways ?? NaN);
      if (Number.isNaN(total)) { ultimo = "resposta inesperada"; continue; }
      const pct = f.vias_total ? Math.round((total / f.vias_total) * 1000) / 10 : null;   // % das vias da área
      return { mudou: total > 0, vias_alteradas: total, desde: f.base, percentual: pct };
    } catch (err) {
      ultimo = String((err as Error).message ?? err);
    }
  }
  return { mudou: null, vias_alteradas: null, desde: f.base, erro: `Overpass indisponível (${ultimo})` };
}

const dataBr = (iso?: string | null) => (iso ? new Date(iso).toLocaleDateString("pt-BR", { timeZone: "America/Recife" }) : "?");

export async function verificarFontes(
  fontes: Fontes, geradoEm?: string | null, endpoints: string[] = ENDPOINTS,
): Promise<Verificacao> {
  const [ibge, osm] = await Promise.all([checarIbge(fontes.ibge_setores), checarOsm(fontes.osm, endpoints)]);
  const mudou = ibge.mudou === true || osm.mudou === true ? true : (ibge.mudou === null || osm.mudou === null ? null : false);
  const desde = dataBr(geradoEm ?? fontes.osm?.base);
  let resumo: string;
  if (mudou === false) resumo = `Sem atualização nas fontes desde ${desde}. Os dados já estão atualizados.`;
  else if (mudou === true) {
    const partes: string[] = [];
    if (ibge.mudou) partes.push("os setores censitários do IBGE foram republicados");
    if (osm.mudou) {
      const pct = osm.percentual != null ? ` (${String(osm.percentual).replace(".", ",")}% das vias da área)` : "";
      partes.push(`${osm.vias_alteradas} via(s) mudaram no OpenStreetMap na área${pct}`);
    }
    resumo = `Há atualização desde ${desde}: ${partes.join(" e ")}.`;
  } else resumo = `Não foi possível confirmar se há atualização (${ibge.erro ?? osm.erro ?? "fonte indisponível"}).`;
  return { verificado_em: new Date().toISOString(), mudou, ibge, osm, resumo };
}
